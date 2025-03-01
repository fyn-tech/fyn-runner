# Design requirements.

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

# Major Components and Responsibility

The above requirements will be met the use of the following components.

### job manager (Co-ordinator)
- Central component which orchestrates everything between other components
- Manages/Maintains Job Queues
- Determines ability to accept new simulations
- Will contains any misc. configs until we know where to put them

### simulation monitor (observer?)
- Launches and runs simulations
- Tracks progress of simulation
- Tracks resources usage (optional extra)
- Can update/terminate running simulations.
- Reports outcome.

### File manager
- Manages simulation i/o (there where) 
- Synchronisation with cloud and data-back up.
- clean-up of old sims.

### Server Communicator [SC](Server Communicator) (facade - proxy)
- provides api to rest of program for backend communication.
- responsible for raising back end connection and heartbeat.
- handles authentication to server
- communication and data transfer between runner and api (and maybe front end).
  
### Hardware Manager
- Collects system relevant specs for analysis resource availability.
- Detects hardware changes and updates.

### System Integration (SI)
- Installation and registration of the runner.
- Tools for the user to directly interact with the runner (cmd)
- automatic updating?
