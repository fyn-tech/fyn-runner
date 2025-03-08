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
  
### Hardware Manager
- Collects system relevant specs for analysis resource availability.
- Detects hardware changes and updates.

### System Integration
- Installation and registration of the runner.
- Tools for the user to directly interact with the runner (cmd)
- automatic updating?

## Requirements Mapping 

Briefly the requirements will be fulfilled by the following components.

| Requirements                                                                                 | Components                                                                                                                                   |
| -------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| 1. Portability across OSes.                                                                  | [System Integration](#system-integration)                                                                                                    |
| 2. Must start on start up (at least default behaviour).                                      | [System Integration](#system-integration)                                                                                                    |
| 3. Must collect data on hardware of systems.                                                 | [Hardware Manager](#hardware-manager)                                                                                                        |
| 4. Must communicate hardware data to Fyn-api.                                                | [Server Proxy](#server-proxy--facade---proxy),[Hardware Manager](#hardware-manager)                                                          |
| 5. Must communicate with fyn-api regarding job status (starting, monitoring,completion, etc) | [Server Proxy](#server-proxy--facade---proxy) , [Job Manager](#job-manager-co-ordinator), [Simulation Monitor](#simulation-monitor-observer) |
| 6. Must communicate/synchronise simulation data with fyn-api (CRUD on local data).           | [Server Proxy](#server-proxy--facade---proxy), [File manager](#file-manager)                                                                 |
| 7. Must register with fyn-api - storing secret tokens ext.                                   | [Server Proxy](#server-proxy--facade---proxy)                                                                                                |
| 8. Must be able to launch and kill simulations.                                              | [Job Manager](#job-manager-co-ordinator), [Simulation Monitor](#simulation-monitor-observer)                                                 |
| 9. Must organise simulation files.                                                           | [Simulation Monitor](#simulation-monitor-observer), [Server Proxy](#server-proxy--facade---proxy), [File manager](#file-manager)             |


## UML Structure

This section 'transposes' the above into a high level design concept with a uml diagram. Program is in python, so `public`/`private` aren't indicated. Utility methods and attributes are indicted with a `_` prefix. ``<<utility>>`` indicates static or non-object (collection of free functions).

```mermaid
---
title: High Level Runner Class Layout
config:
  class:
    hideEmptyMembersBox: true
---
classDiagram

  %% Relationships
  JobManager *--SimulationMonitor
  JobManager *--ServerProxy
  JobManager *-- FileManager


  SimulationMonitor *-- FileManager
  SimulationMonitor *-- Status
  SimulationMonitor o-- ServerProxy

  ServerProxy *-- APIEndPoint
  ServerProxy *-- MessageQueue
  MessageQueue *-- Message


  %% Classes
  class JobManager {
    %% Attributes:
    List~SimulationMonitor~ simulations
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
  }

  namespace Simulation {

    class SimulationMonitor {
      %% Attributes:
      string name
      Path case_path
      Status status
      Path config_file_path
      thread simulation_monitor

      int _pid
      int _exit_code

      %% Methods:
      launch(config_file_path) -> bool
      terminate() -> bool

      %% launching
      _create_folder_structure() -> bool
      _copy_input_files() -> bool
      _start_execution() -> bool
      _start_monitor_thread() -> thread
    }

    class Status {
      <<enum>>
    } 
  }

  class FileManager {
    %% file_database stores path to folder database
    Path simulation_file_database  
    Path runner_folder
  }
  
  class HardwareManager {
    <<utility>>   
    collect_system_specs()
    detect_hardware_changes()
  }

  namespace Server {
    class ServerProxy {
      %% Attributes:
      APIEndPoint api
      MessageQueue message_queue
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

    class MessageQueue {
      Message[] messages

      is_empty() ->bool
      push_message(Message)
      get_next_message() -> Message      
    } 

    class Message {
      data data
      dataType type
      int priority 
    } 
  }

  class SystemIntegration {
    
  }

 
```