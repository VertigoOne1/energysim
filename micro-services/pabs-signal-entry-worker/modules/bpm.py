#!/bin/python3

import sys, time, os
from logger import setup_custom_logger
sys.path.append(r'./modules')

import traceback
from pprint import pformat
from envyaml import EnvYAML
from camunda.external_task.external_task import ExternalTask

logger = setup_custom_logger(__name__)

if "CONFIG_FILE" in os.environ:
    logger.info("Loading Production Config")
    config = EnvYAML(os.environ.get('CONFIG_FILE'))
else:
    logger.info("Loading Development Config")
    config = EnvYAML('config.yml')

default_bpm_config = {
    "maxTasks": 1,
    "lockDuration": 10000,
    "asyncResponseTimeout": 10000,
    "retries": 3,
    "retryTimeout": 5000,
    "sleepSeconds": 5,
    "isDebug": True,
}

def start_process(process_id, vars, business_key):
    from camunda.client.engine_client import EngineClient
    client = EngineClient()
    result = {}
    if process_id and vars and business_key:
        try:
            logger.debug(f"Starting process - {business_key}")
            logger.debug(f"Variables - {vars}")
            response = client.start_process(process_key=process_id, variables=vars, tenant_id="", business_key=business_key)
            logger.debug(pformat(response))
            result["status"] = "passed"
            result['success'] = True
            result["response"] = response
        except:
            ei = sys.exc_info()
            traceback.print_exception(ei[0], ei[1], ei[2], None, sys.stderr)
            result["reponse"] = traceback.format_exc()
            result['success'] = False
            result["status"] = "failed"
    else:
        result["status"] = "failed"
        result['success'] = False
        result["response"] = f"Insufficient parameters to start process - {process_id} - {business_key} - {vars}"
    return result

def fetch_processes_by_business_key(business_key):
    logger.debug("Fetch processes by business key")
    # localhost:8080/engine-rest/process-instance?businessKey=s96999
    # Response:
#     [
#     {
#         "links": [],
#         "id": "9ae4f808-a8fa-11ec-8e77-0242ac157a02",
#         "definitionId": "MessageToUpdateRouting:2:9dd51e56-a8f0-11ec-8e77-0242ac157a02",
#         "businessKey": "s96999",
#         "caseInstanceId": null,
#         "ended": false,
#         "suspended": false,
#         "tenantId": null
#     }
#    ]
    import requests, traceback, json
    from envyaml import EnvYAML
    config = EnvYAML('config.yml')
    try:
        url = f"{config['camunda']['engine_url']}/process-instance?businessKey={business_key}"
        headers = {"Content-Type":"application/json"}
        pload = {}
        logger.debug(f"URL Result")
        logger.debug(f"{url}")
        logger.debug(f"Payload Result")
        logger.debug(f"{json.dumps(pload)}")
        res = requests.post(url, data = json.dumps(pload), headers = headers)
        logger.debug(f"Raw response")
        logger.debug(f"{res.text}")
        response = json.loads(res.text)
        logger.debug(f"{response}")
        if response:
            try:
                logger.trace("Response received")
                if len(response) == 0:
                    result = {}
                    result["error"] = "No processes by that business key"
                    result["process_ids"] = []
                    return dict(success = True, business_key = business_key, response = response, result = result)
                if len(response) > 0:
                    logger.debug("Found process ids that use that business key")
                    result = {}
                    result['success'] = True
                    result["error"] = ""
                    result["process_ids"] = []
                    for res in response:
                        logger.debug(f"Add - {res['id']}")
                        result["process_ids"].append(res["id"])
                    logger.debug(result)
                    return dict(success = True, business_key = business_key, response = response, result = result)
            except Exception:
                if response["type"] and response["type"] == "RestException":
                    logger.debug(f"{response}")
                    return dict(success = False, business_key = business_key, response = response, result = {})
                else:
                    logger.error("Bad reponse, investigate")
                    logger.error(f"{response}")
                    return dict(success = False, business_key = business_key, response = response, payload = pload)
        else:
            logger.error("No response from camunda")
            logger.error(f"{response}")
            return dict(success = False, business_key = business_key, response = {}, result = {})
    except Exception:
        logger.error(traceback.format_exc())
        logger.error("exception")
        return dict(success = False, business_key = business_key, error = traceback.format_exc())

def fetch_activities_by_process_id(proc_id):
    # localhost:8080/engine-rest/process-instance/{proc_id}/activity-instances
    # Response:
    # {
    #     "id": "2089e724-a957-11ec-8e77-0242ac157a02",
    #     "parentActivityInstanceId": null,
    #     "activityId": "SignalProcessing:9:a62efcdf-a880-11ec-8e77-0242ac157a02",
    #     "activityType": "processDefinition",
    #     "processInstanceId": "2089e724-a957-11ec-8e77-0242ac157a02",
    #     "processDefinitionId": "SignalProcessing:9:a62efcdf-a880-11ec-8e77-0242ac157a02",
    #     "childActivityInstances": [
    #         {
    #             "id": "Activity_0yoqmn4:23cab9d0-a957-11ec-8e77-0242ac157a02",
    #             "parentActivityInstanceId": "2089e724-a957-11ec-8e77-0242ac157a02",
    #             "activityId": "Activity_0yoqmn4",
    #             "activityType": "subProcess",
    #             "processInstanceId": "2089e724-a957-11ec-8e77-0242ac157a02",
    #             "processDefinitionId": "SignalProcessing:9:a62efcdf-a880-11ec-8e77-0242ac157a02",
    #             "childActivityInstances": [
    #                 {
    #                     "id": "ReviewEntryFailure:2e22dc6f-a95a-11ec-8e77-0242ac157a02",
    #                     "parentActivityInstanceId": "Activity_0yoqmn4:23cab9d0-a957-11ec-8e77-0242ac157a02",
    #                     "activityId": "ReviewEntryFailure",
    #                     "activityType": "userTask",
    #                     "processInstanceId": "2089e724-a957-11ec-8e77-0242ac157a02",
    #                     "processDefinitionId": "SignalProcessing:9:a62efcdf-a880-11ec-8e77-0242ac157a02",
    #                     "childActivityInstances": [],
    #                     "childTransitionInstances": [],
    #                     "executionIds": [
    #                         "23ca92bf-a957-11ec-8e77-0242ac157a02"
    #                     ],
    #                     "activityName": "Review Entry Failure",
    #                     "incidentIds": [],
    #                     "incidents": [],
    #                     "name": "Review Entry Failure"
    #                 }
    #             ],
    #             "childTransitionInstances": [],
    #             "executionIds": [
    #                 "23ca92bf-a957-11ec-8e77-0242ac157a02"
    #             ],
    #             "activityName": "Market Entry Point Sub-Process",
    #             "incidentIds": [],
    #             "incidents": [],
    #             "name": "Market Entry Point Sub-Process"
    #         }
    #     ],
    #     "childTransitionInstances": [],
    #     "executionIds": [
    #         "2089e724-a957-11ec-8e77-0242ac157a02"
    #     ],
    #     "activityName": "Signal Processing",
    #     "incidentIds": [],
    #     "incidents": [],
    #     "name": "Signal Processing"
    # }
    import requests, traceback, json
    from envyaml import EnvYAML
    config = EnvYAML('config.yml')
    try:
        url = f"{config['camunda']['engine_url']}/process-instance/{proc_id}/activity-instances"
        headers = {"Content-Type":"application/json"}
        pload = {}
        logger.trace(f"Payload Result")
        logger.trace(f"{json.dumps(pload)}")
        res = requests.get(url, data = json.dumps(pload), headers = headers)
        logger.trace(f"Raw response")
        logger.trace(f"{res.text}")
        logger.trace(f"Status Code: {res.status_code}")
        response = json.loads(res.text)
        logger.trace(f"{response}")
        if response:
            try:
                logger.trace("Response received")
                if len(response) == 0:
                    result = {}
                    result["error"] = "unhandled response from camunda"
                    return dict(success = False, business_key = proc_id, response = response, result = result)
                if len(response) > 0:
                    if response["id"] and response["activityId"] and response["processDefinitionId"]:
                        logger.debug("Process id found")
                        result = {}
                        result['success'] = True
                        result["error"] = ""
                        return dict(success = True, process_id = proc_id, result = result, response = response)
                    elif response["type"] == "InvalidRequestException" and res.status_code == 404:
                        logger.debug(f"Process id not found - {proc_id}")
                        result = {}
                        result['success'] = True
                        result["error"] = f"No process by that id in camunda - {proc_id}"
                        return dict(success = True, process_id = proc_id, result = result, response = {})
                    else:
                        logger.error("Unexpected response")
                        logger.error(f"{response}")
                    return dict(success = False, process_id = proc_id, response = response, result = {})
            except Exception:
                if response["type"] and response["type"] == "RestException":
                    logger.debug(f"{response}")
                    return dict(success = False, process_id = proc_id, response = response, result = {})
                elif response["type"] == "InvalidRequestException" and res.status_code == 404:
                        logger.debug(f"Process id not found - {proc_id}")
                        result = {}
                        result['success'] = True
                        result["error"] = f"No process by that id in camunda - {proc_id}"
                        return dict(success = True, process_id = proc_id, result = result, response = {})
                else:
                    logger.error("Bad reponse, investigate")
                    logger.error(f"{response}")
                    return dict(success = False, process_id = proc_id, response = response, payload = pload)
        else:
            logger.error("No response from camunda")
            logger.error(f"{response}")
            return dict(success = False, process_id = proc_id, response = {}, result = {})
    except Exception:
        logger.error(traceback.format_exc())
        logger.error("exception")
        return dict(success = False, process_id = proc_id, error = traceback.format_exc())

def filter_active_processes_by_process_definition(processes, definition):
    logger.debug(f"Filtering process list by definition - {definition}")
    logger.trace(f"{processes}")
    result = {}
    result['success'] = True
    result['processes'] = []
    result['result'] = {}
    result['result']['process_ids'] = []
    if len(processes) > 0:
        for index in range(len(processes)):
            if not processes[index]['ended'] and definition in processes[index]['definitionId']:
                result['result']['process_ids'].append(processes[index])
                result['success'] = True
        return result
    else:
        return result

def filter_active_processes_by_buskey(processes, buskey):
    logger.debug(f"Filtering process list by business key - {buskey}")
    logger.trace(f"{processes}")
    result = {}
    result['success'] = True
    result['processes'] = []
    result['result'] = {}
    result['result']['process_ids'] = []
    if len(processes) > 0:
        for index in range(len(processes)):
            if not processes[index]['ended'] and buskey in processes[index]['businessKey']:
                result['result']['process_ids'].append(processes[index])
                result['success'] = True
                logger.debug("Active Processes - ")
                logger.debug(f"{result}")
        return result
    else:
        return result

def resolve_current_process_task(activity_instancep):
    logger.debug("Resolving the position of the process")
    logger.trace(f"{activity_instancep}")
    if activity_instancep['success']:
        activity_instance = activity_instancep['response']
    else:
        activity_instance = {}
        activity_instance['id'] = ""
    result = {}
    result["success"] = False
    try:
        if activity_instance["id"]:
            logger.trace("In process")
            if activity_instance["childActivityInstances"] and len(activity_instance["childActivityInstances"]) > 0:
                logger.trace("Active in child process")
                for child in activity_instance["childActivityInstances"]:
                    if child["activityType"] == "subProcess":
                        logger.trace(f"process is busy in subprocess - {child['activityId']}")
                        logger.trace(f"descending into subprocess")
                        for task in child["childActivityInstances"]:
                            if len(task["childActivityInstances"]) == 0:
                                result["success"] = True
                                result["activity_id"] = task['activityId']
                                result["activity_type"] = task['activityType']
                                result["name"] = task['name']
                                logger.trace(f"{result}")
                                return result
                    else:
                        logger.trace(f"process is at {child['activityId']}")
                        result["success"] = True
                        result["activity_id"] = child['activityId']
                        result["activity_type"] = child['activityType']
                        result["name"] = child['name']
                        logger.debug(f"{result}")
                        return result
            else:
                logger.debug("No child instance, process is busy at highest level")
                result["success"] = True
                result["activity_id"] = activity_instance['activityId']
                result["activity_type"] = activity_instance['activityType']
                result["name"] = activity_instance['name']
                logger.debug(f"{result}")
                return result
        else:
            logger.debug("Activity instance has no id")
            logger.debug(f"{activity_instance}")
            return result
    except Exception:
        logger.error(traceback.format_exc())
        logger.error("exception resolving active task")
        return dict(success = False, activity_instance = activity_instance, error = traceback.format_exc())

def bpm_send_message(process_id, business_key, message_name, process_vars):
    import requests, traceback, json
    from envyaml import EnvYAML
    config = EnvYAML('config.yml')
    try:
        procid = fetch_activities_by_process_id(process_id)
        if procid['success']:
            logger.debug("Process ID matched, continuing sending message")
            if process_vars:
                logger.debug("Processing variables into Camunda format")
                proc_var = {}
                for item, value in process_vars.items():
                    logger.trace(f"{item}")
                    proc_var[item] = {}
                    if isinstance(value,(float)):
                        proc_var[item]['value'] = f'{value:.8f}'
                        proc_var[item]['type'] = "String"
                        proc_var[item]['valueInfo'] = {}
                    elif isinstance(value,(bool)):
                        proc_var[item]['value'] = value
                        proc_var[item]['type'] = "Boolean"
                        proc_var[item]['valueInfo'] = {}
                    elif isinstance(value,(dict)):
                        proc_var[item]['value'] = json.dumps(value)
                        proc_var[item]['type'] = "Object"
                        proc_var[item]['valueInfo'] = {}
                        proc_var[item]['valueInfo']["objectTypeName"] = "Java.util.Dictionary"
                        proc_var[item]['valueInfo']["serializationDataFormat"] = "application/json"
                    else:
                        proc_var[item]['value'] = value
                        proc_var[item]['type'] = "String"
                        proc_var[item]['valueInfo'] = {}
                logger.trace("Converted process variables for message")
                logger.debug(proc_var)
                time.sleep(0.17)
            else:
                proc_var = {}
            try:
                url = f"{config['camunda']['engine_url']}/message"
                headers = {"Content-Type":"application/json"}
                pload = {
                    "messageName": message_name,
                    "businessKey": business_key,
                    "processInstanceId": process_id,
                    "correlationKeys" : {},
                    "processVariables" : proc_var,
                    "resultEnabled" : "True"
                }
                logger.trace(f"Payload Result")
                logger.trace(f"{json.dumps(pload)}")
                res = requests.post(url, data = json.dumps(pload), headers = headers)
                response = json.loads(res.text)
                if response:
                    logger.trace("Response received")
                    try:
                        if response[0]['resultType'] == "Execution":
                            logger.debug("Message send success")
                            return dict(success = True, response = response, payload = pload)
                    except Exception:
                        if response["type"] == "InvalidRequestException":
                            logger.error("Bad reponse, investigate")
                            logger.error(f"{response}")
                            return dict(success = False, response = response, payload = pload)
                        if response["type"] == "RestException":
                            if "MismatchingMessageCorrelationException" in response["message"]:
                                logger.warn("Message was not expected at the process state")
                                logger.debug(f"{response}")
                                return dict(success = True, response = "message_unexpected", payload = pload)
                            else:
                                logger.warn("non Execution response received, might still be ok")
                                logger.debug(f"{response}")
                                return dict(success = False, response = response, payload = pload)
                        else:
                            logger.error("Bad response from Camunda, investigate")
                            logger.error("Payload")
                            logger.error(f"{pload}")
                            logger.error("Response")
                            logger.error(f"{response}")
                            return dict(success = False, response = response, payload = pload)
                else:
                    logger.error("No response from camunda")
                    logger.error(f"{response}")
                    return dict(success = False, response = {}, payload = pload)
            except Exception:
                logger.error(traceback.format_exc())
                logger.error("exception")
                return dict(success = False, process_id = process_id, error = traceback.format_exc())
        else:
            logger.error("ProcessID not found")
            return dict(success = False, response = "process_id not found", payload = {})
    except Exception:
        logger.error(traceback.format_exc())
        logger.error("exception")
        return dict(success = False, process_id = process_id, error = traceback.format_exc())

def bpm_send_process_start_message(business_key, message_name, process_vars):
    import requests, traceback, json
    from envyaml import EnvYAML
    config = EnvYAML('config.yml')
    try:
        if process_vars:
            logger.trace("Processing variables into Camunda format")
            proc_var = {}
            for item, value in process_vars.items():
                logger.trace(f"{item}")
                proc_var[item] = {}
                if isinstance(value,(float)):
                    proc_var[item]['value'] = f'{value:.8f}'
                    proc_var[item]['type'] = "String"
                    proc_var[item]['valueInfo'] = {}
                elif isinstance(value,(bool)):
                    proc_var[item]['value'] = value
                    proc_var[item]['type'] = "Boolean"
                    proc_var[item]['valueInfo'] = {}
                elif isinstance(value,(dict)):
                    proc_var[item]['value'] = json.dumps(value)
                    proc_var[item]['type'] = "Object"
                    proc_var[item]['valueInfo'] = {}
                    proc_var[item]['valueInfo']["objectTypeName"] = "Java.util.Dictionary"
                    proc_var[item]['valueInfo']["serializationDataFormat"] = "application/json"
                else:
                    proc_var[item]['value'] = value
                    proc_var[item]['type'] = "String"
                    proc_var[item]['valueInfo'] = {}
            logger.trace("Converted process variables for message")
            logger.debug(proc_var)
            time.sleep(0.17)
        else:
            proc_var = {}
        try:
            url = f"{config['camunda']['engine_url']}/message"
            headers = {"Content-Type":"application/json"}
            pload = {
                "messageName": message_name,
                "businessKey": business_key,
                "correlationKeys" : {},
                "processVariables" : proc_var,
                "resultEnabled" : "True"
            }
            logger.trace(f"Payload Result")
            logger.trace(f"{json.dumps(pload)}")
            res = requests.post(url, data = json.dumps(pload), headers = headers)
            response = json.loads(res.text)
            if response:
                logger.debug("Response received")
                logger.trace(f"{response}")
                try:
                    if response[0]['resultType'] == "ProcessDefinition":
                        logger.debug("Process start success - id - ")
                        logger.debug(f"{response[0]['processInstance']['id']}")
                        return dict(success = True, response = response, process_id = response[0]['processInstance']['id'])
                    else:
                        return dict(success = True, response = response, payload = pload)
                except Exception:
                    if response["type"] == "InvalidRequestException":
                        logger.error("Bad reponse, investigate")
                        logger.error(f"{response}")
                        return dict(success = False, response = response, payload = pload)
                    if response["type"] == "RestException":
                        if "MismatchingMessageCorrelationException" in response["message"]:
                            logger.debug(f"{response}")
                            logger.debug("Message was not expected at the process state")
                            return dict(success = True, response = "message_unexpected", payload = pload)
                        else:
                            logger.warn("non Execution response received, might still be ok")
                            logger.debug(f"{response}")
                            return dict(success = False, response = response, payload = pload)
                    else:
                        logger.error("Bad response from Camunda, investigate")
                        logger.error("Payload")
                        logger.error(f"{pload}")
                        logger.error("Response")
                        logger.error(f"{response}")
                        return dict(success = False, response = response, payload = pload)
            else:
                logger.error("No response from camunda")
                logger.error(f"{response}")
                return dict(success = False, response = {}, payload = pload)
        except Exception:
            logger.error(traceback.format_exc())
            logger.error("exception")
            return dict(success = False, error = traceback.format_exc())
    except Exception:
        logger.error(traceback.format_exc())
        logger.error("exception")
        return dict(success = False, error = traceback.format_exc())