# Runner High Level Design
## Design requirements.

Requirements of a the fyn-runner (presently unordered):
1. Portability across OSes.
2. Must start on start up (at least default behaviour).
3. Must collect data on hardware of systems.
4. Must communicate hardware data to Fyn-api.
5. Must communicate with fyn-api regarding job status (starting, monitoring,completion, etc)
6. Must communicate/synchronise simulation data with fyn-api (CRUD on local data).
7. Must register with fyn-api - storing secret tokens ext.
8. Must be able to launch and kill simulations.
9. Must organise simulation files.

## Major Components and Responsibility

The above requirements will be met the use of the following components.

### Job Manager (Co-ordinator)
- Central component which orchestrates everything between other components
- Manages/Maintains job queues, priorities, etc
- Determines ability to accept new simulations
- Will contains any misc. configs until we know where to put them

### Simulation Monitor (observer?)
- Launches and runs simulations
- Tracks progress of simulation
- Tracks resources usage (optional extra)
- Can update/terminate running simulations.
- Reports outcome.

### File manager
- Manages simulation i/o (there where)
- Synchronisation with cloud and data-back up.
- clean-up of old sims.

### Server Proxy  (facade - proxy)
- provides api to rest of program for backend communication.
- responsible for raising back end connection and heartbeat.
- handles authentication to server
- communication and data transfer between runner and api (and maybe front end).

### System Integration
- Collects system relevant specs for analysis resource availability.
- Detects hardware changes and updates.
- Installation and registration of the runner.
- Tools for the user to directly interact with the runner (cmd)
- automatic updating?

## Requirements Mapping

Briefly the requirements will be fulfilled by the following components.

| Requirements                                                                                 | Components                                                                                                                                  |
| -------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| 1. Portability across OSes.                                                                  | [System Integration](#system-integration)                                                                                                   |
| 2. Must start on start up (at least default behaviour).                                      | [System Integration](#system-integration)                                                                                                   |
| 3. Must collect data on hardware of systems.                                                 | [System Integration](#system-integration)                                                                                                   |
| 4. Must communicate hardware data to Fyn-api.                                                | [Server Proxy](#server-proxy--facade---proxy), [System Integration](#system-integration)                                                    |
| 5. Must communicate with fyn-api regarding job status (starting, monitoring,completion, etc) | [Server Proxy](#server-proxy--facade---proxy), [Job Manager](#job-manager-co-ordinator), [Simulation Monitor](#simulation-monitor-observer) |
| 6. Must communicate/synchronise simulation data with fyn-api (CRUD on local data).           | [Server Proxy](#server-proxy--facade---proxy), [File manager](#file-manager)                                                                |
| 7. Must register with fyn-api - storing secret tokens ext.                                   | [Server Proxy](#server-proxy--facade---proxy)                                                                                               |
| 8. Must be able to launch and kill simulations.                                              | [Job Manager](#job-manager-co-ordinator), [Simulation Monitor](#simulation-monitor-observer)                                                |
| 9. Must organise simulation files.                                                           | [Simulation Monitor](#simulation-monitor-observer), [Server Proxy](#server-proxy--facade---proxy), [File manager](#file-manager)            |


## UML Structure

This section 'transposes' the above into a high level design concept with a uml class diagram. The runner will be in python, so `public`/`private` aren't indicated. Utility methods and attributes are indicted with a `_` prefix. ``<<utility>>`` indicates static or non-object (collection of free functions).

```mermaid
---
title: High Level Runner Class Layout
config:
  class:
    hideEmptyMembersBox: true
---
classDiagram

  %% Relationships
  JobManager *--Job
  JobManager *--ServerProxy
  JobManager *-- FileManager

  Job o-- ServerProxy
  Job *-- FileManager

  ServerProxy *-- APIEndPoint
  ServerProxy *-- Message

  FileManager *-- RunnerConfig


  %% Classes
  class JobManager {
    %% FIXME: Hardware/system info stuff is not in the job manager.
    %% Attributes:
    PriorityQueue~Job~ job_queue
    ServerProxy backend_communicator

    %% Methods:
    %% public interface/facade:
    start_up()
    shut_down()

    %% Startup procedures
    _load_configuration()
    _raise_server_connection()
    _check_system_hardware()

    %% Startup procedures
    _end_server_connection()
    _save_configuration()

    %% API communication (exc. sim file sync.)
    _respond_to_job_request()
    _update_hardware_data()
    _heart_beat()
  }

  namespace Simulation {

    class Job {
      %% Attributes:

      %% Python object attributes
      CompletedProcess _job_result

      %% Robber clients
      FileManager file_manager
      Path case_directory
      Logger logger
      ServerProxy server_proxy

      %% OpenAPI client
      JobInfoRunner job
      App application
      ActiveJobTracker _job_activity_tracker
      ApplicationRegistryApi _app_reg_api
      JobManagerApi _job_api

      %% Methods
      __init__()
      launch()

      %% Main Control Functions
      _setup()
      _run()
      _clean_up()

      %% Setup Functions
      _setup_local_simulation_directory()
      _fetching_simulation_resources()
      _handle_application(file)
      _download_resource_file(UUID)

      %% Run Functions
      _run_application()

      %% Clean Up Functions
      _upload_application_results()
      _report_application_result()

      %% Misc
      _update_status(StatusEnum)

    }
  }

  class FileManager {
    %% file_database stores path to folder database
    Path simulation_file_database
    Path runner_folder
    RunnerConfig: config
  }

  namespace Server {
    class ServerProxy {
      %% Attributes:
      APIEndPoint api
      PriorityQueue~Message~ message_queue
      Dict~str, observer_call_back[]~ observer_list
      thread _outgoing_message_handler
      thread _incoming_message_handler

      %% Method:
      push_message(Message) -> bool
      register_observer(str, observer_call_back(Message)) -> bool
      unregister_observer(str) -> bool
      notify_observers(Message) -> bool

      %% Backend communication
      _raise_connection()
      _fetch_api() -> APIEndPoint
      _send_message(Message) -> bool
      _listen_api()
    }

    class APIEndPoint {
      <<enum>>
    }

    class Message {
      data data
      MessageType type
      int priority
    }
  }

  class SystemIntegration {
    <<utility>>
    collect_system_info()
  }
```

## General Error Handling and Logging Approach:

In general the runner needs to be 'fault' tolerant and should try to 'keep' running even when errors do occur. Thus general crashes when errors are encountered are to be minimised. Logging will be added to the program, and configurable and reportable to the server to help identify bugs and problems. Generally for levels of messaging the following hierarchical structure is followed:

- Debugging: Additional information for diagnosing problems.
- Info: General information and progress updates.
- Warning: Some assumptions are being made to proceed, which may lead to further issues.
- Error: An serious problem has occurred by the program will attempt to continue.
- Critical: No way to continue, exit program.

In general simulations should not be terminated if the runner goes down. At some point in the future we will have a 're-attach' to running simulation. That say a runner going down should not propagate to the simulation.
