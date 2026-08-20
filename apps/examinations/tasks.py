from celery import shared_task

from apps.examinations.services.imports import process_examination_import


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def process_examination_import_task(self, import_id):
    process_examination_import(import_id)
