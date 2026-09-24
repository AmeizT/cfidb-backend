from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("users", "0031_alter_user_recovery_email"), ("churches", "0053_zone_avatar")]
    operations = [migrations.AddField(model_name="user", name="regional_zone", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="churches.zone"))]
