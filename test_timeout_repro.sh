#!/bin/bash
# Reproduction script for timeout behavior
TIMEOUT_SEC=5

cleanup() {
    echo "Cleaning up..."
    if [ -n "$TIMEOUT_PID" ]; then
        kill "$TIMEOUT_PID" 2>/dev/null
    fi
}

trap 'cleanup; exit 1' SIGINT SIGTERM

(
    sleep $TIMEOUT_SEC
    echo "TIMEOUT TRIGGERED! Killing main process $$"
    kill -9 $$
) &
TIMEOUT_PID=$!

echo "Starting child process that sleeps for 20s..."
# Simulating launch.command which calls python
sleep 20 &
CHILD_PID=$!
echo "Child PID: $CHILD_PID"

wait $CHILD_PID
echo "Child process finished naturally."
cleanup
