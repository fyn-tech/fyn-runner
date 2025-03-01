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


