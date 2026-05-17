"""Escenario de carga para MediaIntel.

Uso (desde la raiz del proyecto):

    docker run --rm -p 8089:8089 -v $(pwd)/loadtests:/mnt/locust \
      locustio/locust -f /mnt/locust/locustfile.py \
      --host http://host.docker.internal:8000

Luego abrir http://localhost:8089 y disparar 10 / 50 / 100 usuarios.
"""

from __future__ import annotations

import io
import random
import uuid

from locust import HttpUser, between, task

DEMO_EMAIL = "analyst@mediaintel.local"
DEMO_PASSWORD = "ChangeMe123!"

_PRIORITIES = ["low", "medium", "high", "critical"]


def _fake_text() -> bytes:
    snippets = [
        b"Hola, hoy fue un dia tranquilo en la oficina.",
        b"Te voy a golpear si no respondes, idiota.",
        b"Me siento triste y sin energia, no quiero seguir.",
        b"This is total shit and I hate everything.",
        b"Reunion programada manana 9am, traer informe.",
    ]
    return random.choice(snippets)


class MediaIntelUser(HttpUser):
    wait_time = between(0.5, 2.0)

    def on_start(self):
        resp = self.client.post(
            "/api/v1/auth/login",
            json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
            name="auth.login",
        )
        if resp.status_code != 200:
            raise RuntimeError(
                f"No se pudo iniciar sesion ({resp.status_code}): {resp.text}"
            )
        self.token = resp.json()["access_token"]
        self.client.headers.update({"Authorization": f"Bearer {self.token}"})

    @task(5)
    def create_case_text_only(self):
        filename = f"loadtest-{uuid.uuid4()}.txt"
        files = {"files": (filename, io.BytesIO(_fake_text()), "text/plain")}
        data = {
            "title": f"loadtest {uuid.uuid4()}",
            "priority": random.choice(_PRIORITIES),
        }
        self.client.post(
            "/api/v1/cases",
            data=data,
            files=files,
            name="cases.create_text",
        )

    @task(2)
    def list_cases(self):
        self.client.get("/api/v1/cases?page_size=20", name="cases.list")

    @task(1)
    def health(self):
        self.client.get("/health", name="health")
