#!/bin/bash

# Smart Log Analyzer
# Location: /Users/axrid/Documents/EVM/information-ai/auto/log_analyzer.sh

# Exit codes
STATUS_NORMAL=0
STATUS_WARNING=1
STATUS_CRITICAL=2

# Default configuration
LOG_DIR="/tmp"
LOG_GLOB="autowake_*.log"
TIME_WINDOW_MINS=1440 # 24 hours
VERBOSE=false

# Usage information
usage() {
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  -d, --dir DIR      Directory to scan (default: /tmp)"
    echo "  -p, --pattern PAT  Log file pattern (default: autowake_*.log)"
    echo "  -t, --time MINS    Time window in minutes (default: 1440)"
    echo "  -v, --verbose      Enable detailed output"
    echo "  -h, --help         Show this help"
}

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        -d|--dir) LOG_DIR="$2"; shift ;;
        -p|--pattern) LOG_GLOB="$2"; shift ;;
        -t|--time) TIME_WINDOW_MINS="$2"; shift ;;
        -v|--verbose) VERBOSE=true ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown parameter: $1"; usage; exit 1 ;;
    esac
    shift
done

# Initialize analysis
FINAL_STATUS=$STATUS_NORMAL
CRITICAL_FINDINGS=()
WARNING_FINDINGS=()

# Find relevant log files modified in the last 24 hours
LOG_FILES=$(find "$LOG_DIR" -name "$LOG_GLOB" -mmin -"$TIME_WINDOW_MINS" 2>/dev/null)

if [ -z "$LOG_FILES" ]; then
    echo "[INFO] No log files found in $LOG_DIR matching $LOG_GLOB within the last $TIME_WINDOW_MINS minutes."
    exit $STATUS_NORMAL
fi

# Define Search Patterns
# CRITICAL Patterns
# 1. CPU Temp > 85 (Matches strings like "CPU temperature: 86.5 C" or "Temp: 90")
# 2. Memory Exhausted
# 3. Disk Space Low
# 4. Deadlock
CRITICAL_REGEX="(CPU (temp|temperature).*(8[6-9]|9[0-9]|1[0-9][0-9])|Out of memory|Memory exhausted|Disk space low|No space left|Deadlock detected)"

# WARNING Patterns
# 1. Network failure but recovery
# 2. Process timeout
# 3. Too many temp files
# 4. Config warnings
WARNING_REGEX="(Network connection failed|Connection lost|Process timeout|Too many (temp|temporary) files|Configuration warning|Config error)"

# Process files
while IFS= read -r file; do
    [ -z "$file" ] && continue
    [ "$VERBOSE" = true ] && echo "[DEBUG] Analyzing $file..."

    # Check for Criticals
    MATCHES=$(grep -Ei "$CRITICAL_REGEX" "$file")
    if [ -n "$MATCHES" ]; then
        FINAL_STATUS=$STATUS_CRITICAL
        while read -r line; do
            CRITICAL_FINDINGS+=("$file: $line")
        done <<< "$MATCHES"
    fi

    # Check for Warnings (only if we haven't found criticals or to complete the report)
    MATCHES=$(grep -Ei "$WARNING_REGEX" "$file")
    if [ -n "$MATCHES" ]; then
        [ $FINAL_STATUS -lt $STATUS_WARNING ] && FINAL_STATUS=$STATUS_WARNING
        while read -r line; do
            WARNING_FINDINGS+=("$file: $line")
        done <<< "$MATCHES"
    fi
done <<< "$LOG_FILES"

# Output Summary
echo "------------------------------------------------"
echo "Log Analysis Summary"
echo "Time Window: Last $((TIME_WINDOW_MINS / 60)) hours"
echo "Status: $([ $FINAL_STATUS -eq 2 ] && echo "CRITICAL" || ([ $FINAL_STATUS -eq 1 ] && echo "WARNING" || echo "NORMAL"))"
echo "------------------------------------------------"

if [ ${#CRITICAL_FINDINGS[@]} -gt 0 ]; then
    echo "[CRITICAL ISSUES FOUND]"
    for item in "${CRITICAL_FINDINGS[@]:0:5}"; do
        echo "  - $item"
    done
    [ ${#CRITICAL_FINDINGS[@]} -gt 5 ] && echo "  ... and $((${#CRITICAL_FINDINGS[@]} - 5)) more"
fi

if [ ${#WARNING_FINDINGS[@]} -gt 0 ]; then
    echo "[WARNING ISSUES FOUND]"
    for item in "${WARNING_FINDINGS[@]:0:5}"; do
        echo "  - $item"
    done
    [ ${#WARNING_FINDINGS[@]} -gt 5 ] && echo "  ... and $((${#WARNING_FINDINGS[@]} - 5)) more"
fi

if [ $FINAL_STATUS -eq $STATUS_NORMAL ]; then
    echo "[INFO] No issues detected in analyzed logs."
fi

# Final exit code
exit $FINAL_STATUS
