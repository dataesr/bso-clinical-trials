import redis

from rq import Queue, Connection
from flask import render_template, Blueprint, jsonify, request, current_app

from bso.server.main.tasks import create_task_harvest, create_task_transform_load

main_blueprint = Blueprint("main", __name__, )


@main_blueprint.route("/", methods=["GET"])
def home():
    return render_template("home.html")

@main_blueprint.route("/harvest", methods=["POST"])
def run_task_harvest():
    args = request.get_json(force=True)
    with Connection(redis.from_url(current_app.config["REDIS_URL"])):
        q = Queue("bso-clinical-trials", default_timeout=216000)
        task = q.enqueue(create_task_harvest, args)
    response_object = {
        "status": "success",
        "data": {
            "task_id": task.get_id()
        }
    }
    return jsonify(response_object), 202

@main_blueprint.route("/transform-load", methods=["POST"])
def run_task_transform_load():
    args = request.get_json(force=True)
    with Connection(redis.from_url(current_app.config["REDIS_URL"])):
        q = Queue("bso-clinical-trials", default_timeout=21600)
        task = q.enqueue(create_task_transform_load, args)
    response_object = {
        "status": "success",
        "data": {
            "task_id": task.get_id()
        }
    }
    return jsonify(response_object), 202

@main_blueprint.route("/tasks/<task_id>", methods=["GET"])
def get_status(task_id):
    with Connection(redis.from_url(current_app.config["REDIS_URL"])):
        q = Queue("bso-clinical-trials")
        task = q.fetch_job(task_id)
    if task:
        response_object = {
            "status": "success",
            "data": {
                "task_id": task.get_id(),
                "task_status": task.get_status(),
                "task_result": task.result,
            },
        }
    else:
        response_object = {"status": "error"}
    return jsonify(response_object)
