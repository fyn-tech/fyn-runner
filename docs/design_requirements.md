# Design requirements.

Requirements of a the fyn-runner (presently unordered):
- Protability accorss OSes.
- Must start on start up (at least default behaviour).
- Must collect data on hardware of systems.
- Must communicate hardware data to Fyn-api.
- Must communicate with fyn-api regarding job status (starting, monitoring,completion, etc)
- Must communicate/synchronise simulation data with fyn-api (CRUD on local data).
- Must register with Fyn-Api - storing secret tokens ext.
- Must be able to launch and kill simulations.
- Must organise simulation files.