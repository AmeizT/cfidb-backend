import json
import re
import time
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.conf import settings
from django.db import DatabaseError, transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, Throttled, ValidationError

from .context import resolve_jethro_context
from .models import JethroActionLog, JethroConversation, JethroMessage, JethroUsageLog
from .tools import execute_tool, tool_schemas


SAFE_PROVIDER_ERROR = "Jethro could not complete that request. Please try again."
READ_ONLY_WORDS = re.compile(r"\b(create|update|edit|delete|remove|approve|transfer|submit|change)\b", re.I)


class JethroProviderError(Exception):
    pass


def _prompt():
    return (Path(__file__).parent / "prompts" / "system_v1.txt").read_text()


def _title(message):
    words = message.split()
    return " ".join(words[:8])[:120] or "New conversation"


def _sanitise(arguments):
    clean = {}
    for key, value in arguments.items():
        if isinstance(value, str):
            clean[str(key)[:50]] = value[:200]
        elif isinstance(value, (int, float, bool)) or value is None:
            clean[str(key)[:50]] = value
        elif isinstance(value, (Decimal, date)):
            clean[str(key)[:50]] = str(value)
    return clean


def _record_tool(context, conversation, name, arguments):
    started = time.monotonic()
    status = JethroActionLog.Status.SUCCESS
    error = ""
    try:
        # Give every tool its own savepoint. If a database write fails, Django
        # rolls back to this boundary before we attempt to write the audit row.
        with transaction.atomic():
            result = execute_tool(name, arguments, context, conversation)
        return result
    except ValidationError as exc:
        status = JethroActionLog.Status.REJECTED
        error = "Invalid or unsupported tool arguments."
        raise
    except PermissionDenied:
        status = JethroActionLog.Status.REJECTED
        error = "Permission denied."
        raise
    except Exception as exc:
        status = JethroActionLog.Status.ERROR
        error = "Tool execution failed."
        raise
    finally:
        try:
            with transaction.atomic():
                JethroActionLog.objects.create(
                    user=context.user,
                    assembly=context.active_assembly,
                    conversation=conversation,
                    tool_name=name[:80],
                    arguments=_sanitise(arguments),
                    status=status,
                    error_message=error,
                    duration_ms=max(0, int((time.monotonic() - started) * 1000)),
                )
        except DatabaseError:
            # Audit failure must not replace the actionable tool exception.
            pass


def _usage_values(response):
    usage = getattr(response, "usage", None)
    input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
    output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
    details = getattr(usage, "input_tokens_details", None)
    cached = int(getattr(details, "cached_tokens", 0) or 0)
    return input_tokens, cached, output_tokens


def _mock_response(message, context, conversation):
    lower = message.lower()
    today = timezone.localdate()
    if "tithe" in lower and re.search(r"\b(create|record|add)\b", lower):
        amount_match = (
            re.search(r"\btithes?\s+of\s+[$]?([\d,]+(?:\.\d{1,2})?)", message, re.I)
            or re.search(r"\badd\s+[$]?([\d,]+(?:\.\d{1,2})?)\s+tithes?\b", message, re.I)
            or re.search(r"\bfor\s+[$]?([\d,]+(?:\.\d{1,2})?)\s+(?:paid\b|via\b|by\b|using\b)", message, re.I)
        )
        member_match = (
            re.search(r"\btithes?\s+for\s+(.+?)\s+for\s+[$]?[\d,]+", message, re.I)
            or re.search(r"\btithes?\s+(?:of\s+[$]?[\d,]+(?:\.\d{1,2})?\s+)?for\s+(.+?)\s+(?:paid\s+via|via|by|using)\b", message, re.I)
        )
        payment_match = re.search(
            r"\b(?:paid\s+via|via|by|using)\s+([a-z][a-z -]*?)(?=\s+(?:on|reference|ref|with)\b|[.,]|$)",
            message,
            re.I,
        )
        if not amount_match or not member_match or not payment_match:
            return (
                "Please include the member, amount, and payment method—for example: "
                "‘Record a tithe of 2500 for Mary Banda by cash.’",
                None,
            )
        try:
            amount = str(Decimal(amount_match.group(1).replace(",", "")))
        except InvalidOperation:
            return "Please provide a valid tithe amount.", None
        date_match = re.search(r"\bon\s+(20\d{2}-\d{2}-\d{2})\b", message, re.I)
        if not date_match and re.search(
            r"\bon\s+(?:yesterday|tomorrow|\d{1,2}[/-]\d{1,2}|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b)",
            message,
            re.I,
        ):
            return "Please provide the payment date in YYYY-MM-DD format so I can resolve it safely.", None
        reference_match = re.search(r"\b(?:reference|ref)\s*[:#-]?\s*([A-Za-z0-9_-]+)", message, re.I)
        try:
            data = _record_tool(context, conversation, "prepare_tithe_creation", {
                "member_query": " ".join(member_match.group(1).split()),
                "amount": amount,
                "payment_method": " ".join(payment_match.group(1).split()),
                "payment_date": date_match.group(1) if date_match else None,
                "reference": reference_match.group(1) if reference_match else "",
                "notes": "",
            })
        except ValidationError as exc:
            if "payment_method" in exc.detail:
                return "That payment method is not supported. Choose Bank, Cash, Cheque, Mobile Money, or Other.", None
            raise
        if data["type"] == "tithe_confirmation":
            return (
                "Review these tithe details. Nothing will be recorded until you confirm. "
                f"Payment date: {data['draft']['payment_date']}.",
                data,
            )
        if data["results"]:
            return (
                "I found several possible members. Select the correct person to continue. "
                f"Payment date: {data['draft']['payment_date']}.",
                data,
            )
        return (
            "No matching member was found. Search or browse eligible members in this assembly to continue. "
            f"Payment date: {data['draft']['payment_date']}.",
            data,
        )
    if READ_ONLY_WORDS.search(message):
        return (
            "Jethro is read-only in this testing version and cannot change records. "
            "You can use the relevant CFI Workspace screen to complete that action.",
            None,
        )
    if "report" in lower or "outstanding" in lower:
        period_match = re.search(r"\b(20\d{2})-(0[1-9]|1[0-2])\b", message)
        period = period_match.group(0) if period_match else today.strftime("%Y-%m")
        data = _record_tool(context, conversation, "get_report_submission_status", {"period": period})
        text = "No monthly report was found for that period." if data["missing_reports"] else f"The monthly report is {data['results'][0]['status']}."
        return text, data
    if any(word in lower for word in ("how many", "summary", "total", "joined", "active members")):
        period = "current_month" if "month" in lower else "current_year" if "year" in lower else "all_time"
        data = _record_tool(context, conversation, "get_membership_summary", {"period": period})
        values = data["data"]
        return f"Your active assembly has {values['total_members']} members, including {values['active_members']} active members.", data
    if any(word in lower for word in ("search", "find", "member")):
        query = re.sub(r"(?i)\b(search|find|for|member)\b", " ", message)
        query = " ".join(query.split()) or message
        data = _record_tool(context, conversation, "search_members", {"query": query, "limit": 10})
        count = data["count"]
        return (f"I found {count} matching member{'s' if count != 1 else ''}." if count else "No matching members were found.", data)
    return (
        "I can help you search members, review membership totals, check monthly report status, "
        "or explain how to use CFI Workspace. This testing version is read-only.",
        None,
    )


def _include_resolved_tithe_date(text, structured):
    if not structured or not str(structured.get("type", "")).startswith("tithe_"):
        return text
    payment_date = structured.get("payment_date") or (structured.get("draft") or {}).get("payment_date")
    if payment_date and payment_date not in text:
        return f"{text.rstrip()}\nPayment date: {payment_date}."
    return text


def _provider_response(message, context, conversation):
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise JethroProviderError(SAFE_PROVIDER_ERROR) from exc

    if not settings.JETHRO_MODEL:
        raise JethroProviderError("Jethro has not been configured with a model.")

    recent = list(conversation.messages.order_by("-created_at")[: settings.JETHRO_CONTEXT_MESSAGE_LIMIT])
    inputs = [{"role": item.role, "content": item.content} for item in reversed(recent) if item.role in {"user", "assistant"}]
    client = OpenAI(timeout=30.0, max_retries=1)
    totals = [0, 0, 0]
    structured = None
    try:
        for _ in range(settings.JETHRO_MAX_TOOL_ITERATIONS + 1):
            response = client.responses.create(
                model=settings.JETHRO_MODEL,
                instructions=_prompt(),
                input=inputs,
                tools=tool_schemas(),
                max_output_tokens=settings.JETHRO_MAX_OUTPUT_TOKENS,
            )
            usage = _usage_values(response)
            totals = [left + right for left, right in zip(totals, usage)]
            calls = [item for item in response.output if item.type == "function_call"]
            if not calls:
                return response.output_text or "I could not produce a response.", structured, totals
            inputs += response.output
            for call in calls:
                try:
                    arguments = json.loads(call.arguments)
                    result = _record_tool(context, conversation, call.name, arguments)
                    structured = result
                    output = json.dumps(result, default=str)[: settings.JETHRO_MAX_TOOL_RESULT_CHARS]
                    JethroMessage.objects.create(
                        conversation=conversation,
                        role=JethroMessage.Role.TOOL,
                        content=f"{call.name} completed.",
                        structured_content=result,
                    )
                except (json.JSONDecodeError, ValidationError, PermissionDenied):
                    output = json.dumps({"success": False, "error": "The tool request was invalid or not permitted."})
                inputs.append({"type": "function_call_output", "call_id": call.call_id, "output": output})
        raise JethroProviderError("Jethro reached its tool-use limit. Please make the request more specific.")
    except JethroProviderError:
        raise
    except Exception as exc:
        raise JethroProviderError(SAFE_PROVIDER_ERROR) from exc


def _check_daily_limit(user):
    today = timezone.localdate()
    count = JethroMessage.objects.filter(
        conversation__user=user,
        role=JethroMessage.Role.USER,
        created_at__date=today,
    ).count()
    if count >= settings.JETHRO_DAILY_USER_LIMIT:
        raise Throttled(detail="You have reached today’s Jethro testing limit. Please try again tomorrow.")


@transaction.atomic
def send_jethro_message(*, user, message, conversation_id=None):
    if not settings.JETHRO_ENABLED:
        raise PermissionDenied("Jethro is currently disabled.")
    context = resolve_jethro_context(user)
    _check_daily_limit(user)

    if conversation_id:
        conversation = JethroConversation.objects.filter(
            public_id=conversation_id,
            user=user,
            assembly=context.active_assembly,
            is_archived=False,
        ).first()
        if conversation is None:
            raise ValidationError({"conversation_id": "Conversation was not found."})
    else:
        conversation = JethroConversation.objects.create(
            user=user,
            assembly=context.active_assembly,
            title=_title(message),
        )

    JethroMessage.objects.create(conversation=conversation, role=JethroMessage.Role.USER, content=message)
    if settings.JETHRO_MOCK_MODE:
        text, structured = _mock_response(message, context, conversation)
        usage = (0, 0, 0)
        model = "mock"
    else:
        text, structured, usage = _provider_response(message, context, conversation)
        model = settings.JETHRO_MODEL

    text = _include_resolved_tithe_date(text, structured)

    assistant = JethroMessage.objects.create(
        conversation=conversation,
        role=JethroMessage.Role.ASSISTANT,
        content=text,
        structured_content=structured,
    )
    conversation.save(update_fields=["updated_at"])
    input_tokens, cached_tokens, output_tokens = usage
    JethroUsageLog.objects.create(
        user=user,
        conversation=conversation,
        model=model,
        input_tokens=input_tokens,
        cached_input_tokens=cached_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
    )
    return conversation, assistant, {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
    }
