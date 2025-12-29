# Generated manually on 2025-02-24 to establish core Swarm chat models

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='ChatConversation',
            fields=[
                ('conversation_id', models.CharField(max_length=255, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('student', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Chat Conversation',
                'verbose_name_plural': 'Chat Conversations',
            },
        ),
        migrations.CreateModel(
            name='ChatMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sender', models.CharField(max_length=50)),
                ('content', models.TextField()),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('tool_call_id', models.CharField(blank=True, max_length=255, null=True)),
                ('conversation', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='chat_messages',
                    to='swarm.chatconversation',
                )),
            ],
            options={
                'ordering': ['timestamp'],
                'verbose_name': 'Chat Message',
                'verbose_name_plural': 'Chat Messages',
            },
        ),
    ]
