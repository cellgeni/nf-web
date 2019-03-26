import os
from typing import Dict

from flask import Flask, redirect, url_for, render_template, request
from wtforms import Form, StringField

from nf_web.client import ProcessingClient, OddJobClient

app = Flask(__name__, template_folder="../templates", static_folder="../static")

pr = ProcessingClient(os.getenv("PROCESSING_HOST"))
oj = OddJobClient(os.getenv("ODDJOB_HOST"))


class WorkflowForm(Form):

    @classmethod
    def get_form(cls, wf: Dict, formdata=None):
        setattr(cls, "wf", wf)
        for p in wf.get("parameters"):
            setattr(cls, p['name'], StringField(p['name']))
        return cls(formdata)

    def get_params(self) -> Dict:
        params = {}
        for p in self.wf.get("parameters"):
            param = getattr(self, p['name']).data
            params[p["name"]] = param
        return params


@app.route('/')
def hello():
    return redirect(url_for('status'))


@app.route('/status/')
def status():
    template = "status.html"
    oj.trigger_task_job_check()
    workflows = pr.get_jobs()
    statuses = oj.check_job(list(wf['job_id'] for wf in workflows))
    print(statuses)
    for status, wf in zip(statuses, workflows):
        wf['status'] = status['status']
    print(workflows)
    return render_template(template, workflows=workflows)


@app.route('/workflows/')
def workflows():
    template = "workflows.html"
    workflows = pr.get_components()
    return render_template(template, workflows=workflows)


@app.route('/workflow/<wf_id>/', methods=["GET", "POST"])
def workflow(wf_id):
    template = "workflow.html"
    wf = pr.get_component(wf_id)
    if request.method == 'GET':
        form = WorkflowForm.get_form(wf)
        return render_template(template, wf=wf, form=form)
    elif request.method == 'POST':
        form = WorkflowForm.get_form(wf, request.form)
        pr.post_components_groups(component_id=wf_id, group_id="", params=form.get_params())
        oj.trigger_task_job_submit()
        return redirect(url_for("status"))


if __name__ == '__main__':
    app.run()
