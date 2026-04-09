from django.db import migrations


def create_integration_status_cache_table(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    if vendor == "postgresql":
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS integration_status_cache (
            cache_key varchar(255) PRIMARY KEY,
            value text NOT NULL,
            expires timestamp with time zone NOT NULL
        )
        """
    else:
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS integration_status_cache (
            cache_key varchar(255) PRIMARY KEY,
            value text NOT NULL,
            expires datetime NOT NULL
        )
        """
    schema_editor.execute(create_table_sql)
    schema_editor.execute(
        "CREATE INDEX IF NOT EXISTS integration_status_cache_expires ON integration_status_cache (expires)"
    )


def drop_integration_status_cache_table(apps, schema_editor):
    schema_editor.execute("DROP TABLE IF EXISTS integration_status_cache")


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.RunPython(
            create_integration_status_cache_table,
            reverse_code=drop_integration_status_cache_table,
        ),
    ]
