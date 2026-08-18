// Teams admin page logic (loaded via {% static %} from teams_admin.html).
const modal = document.getElementById('confirmDeleteModal');
if (modal) {
  modal.addEventListener('show.bs.modal', function (event) {
    const button = event.relatedTarget;
    const teamId = button?.getAttribute('data-team-id') || '';
    document.getElementById('deleteTeamId').textContent = teamId;
    document.getElementById('deleteTeamIdInput').value = teamId;
  });
}
