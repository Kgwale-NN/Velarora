"""Server-owned exam assignment for agents that upload their own screen."""
from backend.db._core import _conn


def assignment(computer_id):
    row = _conn().execute("SELECT r.id FROM monitoring_run r JOIN run_computer rc ON rc.run_id=r.id "
        "JOIN computer co ON co.id=rc.computer_id JOIN computer_agent ca ON ca.computer_id=co.id "
        "JOIN user u ON u.id=r.started_by JOIN role role ON role.id=u.role_id "
        "WHERE rc.computer_id=? AND co.host_address LIKE 'agent:%' AND ca.enabled=1 "
        "AND r.status='running' AND u.is_active=1 AND role.name='teacher' ORDER BY r.id DESC LIMIT 1",
        (computer_id,)).fetchone()
    return row['id'] if row else None
