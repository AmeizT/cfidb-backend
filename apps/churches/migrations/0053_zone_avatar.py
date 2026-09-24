from django.db import migrations, models
import apps.churches.utils.generate_oklch


from apps.churches.utils.generate_oklch import generate_oklch_color


def backfill(apps, schema_editor):
    Zone = apps.get_model("churches", "Zone")
    alias = schema_editor.connection.alias
    for zone in Zone.objects.using(alias).filter(zone_avatar_fallback="").iterator(chunk_size=500):
        Zone.objects.using(alias).filter(pk=zone.pk, zone_avatar_fallback="").update(zone_avatar_fallback=generate_oklch_color())


class Migration(migrations.Migration):
    dependencies = [("churches", "0052_regional_admin_role")]
    operations = [
        migrations.AddField(model_name="zone", name="zone_avatar", field=models.ImageField(blank=True, upload_to=apps.churches.utils.generate_oklch.zone_images_path)),
        migrations.AddField(model_name="zone", name="zone_avatar_fallback", field=models.CharField(blank=True, max_length=36)),
        migrations.RunPython(backfill, migrations.RunPython.noop),
    ]
