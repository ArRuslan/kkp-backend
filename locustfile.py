import random
import string
from os import urandom

from locust import task, FastHttpUser


class AnimalReportUser(FastHttpUser):
    host = "http://127.0.0.1:8000"

    @task
    def create_report(self):
        with self.rest("POST", "/animal-reports", json={
            "name": "".join(random.choices(string.ascii_letters, k=8)),
            "breed": "".join(random.choices(string.ascii_letters, k=4)),
            "notes": urandom(256).hex(),
            "latitude": random.random() * 10,
            "longitude": random.random() * 10,
            "media_ids": [],
            "gender": random.choice([0, 1, 2]),
        }):
            ...
        # self.client.get("/world")

    # @task(3)
    # def view_items(self):
    #    for item_id in range(10):
    #        self.client.get(f"/item?id={item_id}", name="/item")
    #        time.sleep(1)

    # def on_start(self):
    #    self.client.post("/login", json={"username":"foo", "password":"bar"})
