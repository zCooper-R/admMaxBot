from django.contrib import admin

from .models import BotSettings, BotUser, MenuNode, UserSessionState, WebhookEvent, WebhookOperationLog

admin.site.register(BotSettings)
admin.site.register(MenuNode)
admin.site.register(BotUser)
admin.site.register(UserSessionState)
admin.site.register(WebhookEvent)
admin.site.register(WebhookOperationLog)

