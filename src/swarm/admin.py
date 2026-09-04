"""Django admin registrations.

Herdr agent rows (REQ-21) are also editable on /settings/ and via
``/v1/herdr-agents/``. Admin is a staff fallback — the DaisyUI SPA settings
sheet is not in this tree (ADR-001).
"""

from django.contrib import admin

from swarm.models import HerdrAgent


@admin.register(HerdrAgent)
class HerdrAgentAdmin(admin.ModelAdmin):
    list_display = ("name", "remote_display", "created_at", "updated_at")
    search_fields = ("name", "remote")
    list_filter = ("created_at",)
    readonly_fields = ("created_at", "updated_at")

    @admin.display(description="Remote", ordering="remote")
    def remote_display(self, obj: HerdrAgent) -> str:
        return obj.remote or "localhost (no --remote)"
