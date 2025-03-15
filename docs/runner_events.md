## Installation Process
- need to clean up end.
```mermaid
sequenceDiagram
    participant user
    participant fyn-runner
    participant fyn-api

    user->>fyn-api: Request new runner
    fyn-api-->>user: Responses runner payload
    user->>fyn-runner: Start installation process
    fyn-runner->>fyn-runner: Create local cache/Directory Folder
    fyn-runner->>fyn-runner: Configure/Install Runner
    alt Windows Platform
        fyn-runner->>os-service: Register Windows Service
        Note over fyn-runner,os-service: Uses Windows Service Manager
    else Linux Platform
        fyn-runner->>os-service: Create systemd service file
        fyn-runner->>os-service: Enable systemd service
        Note over fyn-runner,os-service: /etc/systemd/system/
    else MacOS Platform
        fyn-runner->>os-service: Create LaunchDaemon plist
        fyn-runner->>os-service: Load LaunchDaemon
        Note over fyn-runner,os-service: /Library/LaunchDaemons/
    end

    alt Registration Success
        os-service-->>fyn-runner: Service registered
        fyn-runner-->>user: Installation complete
    else Registration Failed
        os-service-->>fyn-runner: Registration failed
        fyn-runner->>fyn-runner: Cleanup installation
        fyn-runner-->>user: Installation failed
    end
```

## Post-Installation Process
```mermaid
sequenceDiagram
    participant user
    participant fyn-runner
    participant fyn-api

    user->>fyn-runner: Start Execution
    fyn-runner->>user: Request runner credentials
    user->>fyn-api: Request runner credentials
    fyn-api->>fyn-api: Generate one-time run credentials
    fyn-api-->>user: Responses runner credentials
    user-->>fyn-runner: Responses runner credentials
    fyn-runner->>fyn-api: Request validate credentials
    alt Valid Credentials
    fyn-api-->>fyn-runner: Respond validate credentials
    fyn-runner->>fyn-api: Request runner registration
    fyn-api->>fyn-api: Generate new 'null runner' with runner ID & Auth.
    fyn-api-->>fyn-runner: Respond runner ID & Auth.
    fyn-runner->>fyn-runner: Save runner ID & Auth.
    fyn-runner-->>user: Report successful registration
    else Invalid
    fyn-api-->>fyn-runner: Respond Invalidate credentials
    fyn-runner-->>user: Report unsuccessful registration
    end
```

## Start up
- connecting to 'running' jobs left for later iteration.
```mermaid
sequenceDiagram
    participant fyn-runner
    participant local cache
    participant fyn-api

    fyn-runner->>+local cache: establish location
    fyn-runner<<->>local cache: load settings
    fyn-runner->>fyn-api: Request Validate with runner ID & Auth
    fyn-api-->>fyn-runner: Respond validate credentials
    fyn-runner->>fyn-api: Report startup state
    fyn-api-->>fyn-runner: Acknowledge startup

    %% Hardware Check
    fyn-runner->>fyn-runner: Collect current hardware data
    fyn-runner->>local cache: Check hardware cache

    alt No Cache Exists
        local cache-->>fyn-runner: Cache missing
        fyn-runner->>local cache: Create hardware cache
        fyn-runner->>fyn-api: Post full hardware data
    else Cache Exists
        local cache-->>fyn-runner: Return cached data
        fyn-runner->>fyn-runner: Compare with current
        alt Hardware Changed
            fyn-runner->>local cache: Update cache
            fyn-runner->>fyn-api: Post hardware updates
        end
    end

    fyn-api-->>fyn-runner: Confirm hardware status

    %% Enter Ready State
    fyn-runner->>fyn-api: Report ready for jobs
    fyn-api-->>fyn-runner: Acknowledge ready for jobs
    fyn-runner->>fyn-runner: Enter Active State
    deactivate local cache
```
## Active State Connection Events
- Once started we enter the main active state.
- We can accept jobs, and will launch new jobs threads when requested - (see Job events for event details.)
- Use web sockets

```mermaid
sequenceDiagram
    box fyn-runner process
        participant main thread
    end
    participant fyn-api


    main thread->>main thread: Enter Active State
    loop Main Active State Loop
        main thread->>fyn-api: Post heartbeat (~every 60s)
        fyn-api-->>main thread: Response Heartbeat acknowledge

        alt Connection Lost
            main thread->>main thread: Enter reconnection state
            loop Until Reconnected (with backoff)
                main thread->>fyn-api: Post with runner ID & Auth
                alt Reconnection Successful
                    main thread->>fyn-api: Request validate with runner ID & Auth
                    fyn-api-->>main thread: Respond validate credentials
                    main thread->>fyn-api: Report ready for jobs
                    fyn-api-->>main thread: Acknowledge ready state
                    main thread->>main thread: Enter Active State
                end
            end
        end
    end
```
## Job Events

- note runtime resource availability must be assessed at boot up for the job (application), failure to meet memory needs (as an example) should result in a crash, which then follows a failed job route.

```mermaid
sequenceDiagram
    box fyn-runner process
        participant main thread
        participant job thread
    end
    participant local cache
    participant fyn-api

    fyn-api->>main thread: Post job request
    main thread->>main thread: determine if able to accept job payload

    alt Sufficient resources/capability to accept job/job payload
        main thread-->>fyn-api: Respond job accepted, waiting for job payload.
        fyn-api->>main thread: Post job payload
        main thread->>local cache: Save job payload
        main thread->>job thread: Spawn thread
        activate job thread
        main thread->>job thread: Assign job
        local cache<<-->>job thread: Get job payload
        job thread->>fyn-api: Report job started
        loop Until Job Complete
            job thread->>job thread: Execute job steps
            job thread->>local cache: Update progress
            job thread->>fyn-api: Report progress + job data (setting based interval)
        end
        job thread->>fyn-api: Report job completion, success/fail
        job thread->>local cache: archive job results
        deactivate job thread
    else Cannot accept Job
        main thread-->>fyn-api: Respond job refused.
    end
```

## Exit and Shutdown

- We don't want to 'terminate jobs' when we exit. If the user shuts down the PC it will be terminated in due course.
- Basically just want to tell the server we have signed off.

```mermaid
sequenceDiagram
    participant fyn-runner
    participant fyn-api

    fyn-runner->>fyn-api: Post shutdown state
    fyn-api-->>fyn-runner: Response shutdown acknowledge
    fyn-runner->>fyn-runner: exit(0)
```

## Missing Events

1. Request for runner data/logs
2. Request for simulation data/logs.
