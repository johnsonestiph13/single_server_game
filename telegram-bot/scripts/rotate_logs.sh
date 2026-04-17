#!/bin/bash
# telegram-bot/scripts/rotate_logs.sh
# Estif Bingo 24/7 - Log Rotation Script
# Automatically rotates, compresses, and cleans up old log files

# ==================== CONFIGURATION ====================

# Log directories
LOG_DIR="../logs"
BACKUP_DIR="../backups/logs"

# Log file patterns
LOG_FILES=(
    "bot.log"
    "game.log"
    "api.log"
    "errors.log"
    "access.log"
    "healthcheck.log"
)

# Rotation settings
MAX_LOG_SIZE_MB=10          # Rotate when log exceeds this size (MB)
MAX_LOG_AGE_DAYS=30         # Delete logs older than this many days
COMPRESS_OLD_LOGS=true      # Compress rotated logs with gzip
ROTATION_COUNT=5            # Number of rotated logs to keep per file

# Archive settings
ARCHIVE_ENABLED=false       # Whether to archive old logs
ARCHIVE_DAYS=90             # Archive logs older than this many days

# Notification settings
ENABLE_NOTIFICATIONS=false  # Send notifications on rotation
BOT_TOKEN=""                # Telegram bot token (if notifications enabled)
ADMIN_CHAT_ID=""            # Admin chat ID (if notifications enabled)

# Load environment variables if available
if [ -f ../.env ]; then
    source ../.env
elif [ -f .env ]; then
    source .env
fi

# Override with env vars if set
if [ -n "$BOT_TOKEN" ]; then
    BOT_TOKEN="$BOT_TOKEN"
fi
if [ -n "$ADMIN_CHAT_ID" ]; then
    ADMIN_CHAT_ID="$ADMIN_CHAT_ID"
fi

# ==================== FUNCTIONS ====================

log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

get_file_size_mb() {
    local file=$1
    if [ -f "$file" ]; then
        du -m "$file" | cut -f1
    else
        echo "0"
    fi
}

rotate_single_log() {
    local log_file=$1
    local log_path="${LOG_DIR}/${log_file}"
    
    if [ ! -f "$log_path" ]; then
        return 0
    fi
    
    local size_mb=$(get_file_size_mb "$log_path")
    
    # Check if rotation is needed
    if [ "$size_mb" -lt "$MAX_LOG_SIZE_MB" ]; then
        return 0
    fi
    
    log_message "Rotating log: $log_file (${size_mb}MB)"
    
    # Rotate existing backups
    for i in $(seq $((ROTATION_COUNT - 1)) -1 1); do
        if [ -f "${LOG_DIR}/${log_file}.${i}.gz" ]; then
            mv "${LOG_DIR}/${log_file}.${i}.gz" "${LOG_DIR}/${log_file}.$((i + 1)).gz"
        fi
    done
    
    # Compress and rotate current log
    if [ "$COMPRESS_OLD_LOGS" = true ]; then
        gzip -c "$log_path" > "${LOG_DIR}/${log_file}.1.gz"
    else
        mv "$log_path" "${LOG_DIR}/${log_file}.1"
    fi
    
    # Create new empty log file
    touch "$log_path"
    
    # Set proper permissions
    chmod 644 "$log_path"
    
    log_message "Rotated: $log_file -> ${log_file}.1.gz"
    
    return 0
}

cleanup_old_logs() {
    log_message "Cleaning up logs older than ${MAX_LOG_AGE_DAYS} days"
    
    # Delete old compressed logs
    find "$LOG_DIR" -name "*.gz" -type f -mtime +${MAX_LOG_AGE_DAYS} -delete
    find "$LOG_DIR" -name "*.1" -type f -mtime +${MAX_LOG_AGE_DAYS} -delete
    find "$LOG_DIR" -name "*.2" -type f -mtime +${MAX_LOG_AGE_DAYS} -delete
    find "$LOG_DIR" -name "*.3" -type f -mtime +${MAX_LOG_AGE_DAYS} -delete
    find "$LOG_DIR" -name "*.4" -type f -mtime +${MAX_LOG_AGE_DAYS} -delete
    find "$LOG_DIR" -name "*.5" -type f -mtime +${MAX_LOG_AGE_DAYS} -delete
    
    # Also clean up any log files that are empty and old
    find "$LOG_DIR" -name "*.log" -type f -size 0 -mtime +7 -delete
    
    log_message "Cleanup completed"
}

archive_old_logs() {
    if [ "$ARCHIVE_ENABLED" != true ]; then
        return 0
    fi
    
    log_message "Archiving logs older than ${ARCHIVE_DAYS} days"
    
    # Create archive directory
    mkdir -p "$BACKUP_DIR"
    
    # Find and archive old logs
    find "$LOG_DIR" -name "*.gz" -type f -mtime +${ARCHIVE_DAYS} | while read -r file; do
        filename=$(basename "$file")
        archive_name="${BACKUP_DIR}/$(date +%Y%m)_${filename}"
        
        if [ ! -f "$archive_name" ]; then
            mv "$file" "$archive_name"
            log_message "Archived: $filename"
        fi
    done
    
    # Clean up old archives (older than 1 year)
    find "$BACKUP_DIR" -name "*.gz" -type f -mtime +365 -delete
    
    log_message "Archiving completed"
}

check_disk_space() {
    local log_dir_size=$(du -sm "$LOG_DIR" 2>/dev/null | cut -f1)
    local backup_dir_size=$(du -sm "$BACKUP_DIR" 2>/dev/null | cut -f1)
    local total_size=$((log_dir_size + backup_dir_size))
    
    log_message "Log directory size: ${log_dir_size}MB"
    log_message "Backup directory size: ${backup_dir_size}MB"
    log_message "Total logs size: ${total_size}MB"
    
    # Warn if logs exceed 1GB
    if [ "$total_size" -gt 1024 ]; then
        log_message "WARNING: Logs total size exceeds 1GB (${total_size}MB)"
        return 1
    fi
    
    return 0
}

send_notification() {
    if [ "$ENABLE_NOTIFICATIONS" != true ]; then
        return 0
    fi
    
    if [ -z "$BOT_TOKEN" ] || [ -z "$ADMIN_CHAT_ID" ]; then
        return 0
    fi
    
    local subject=$1
    local message=$2
    
    local text="📋 *Log Rotation Report*\n\n"
    text+="*Subject:* ${subject}\n"
    text+="*Time:* $(date '+%Y-%m-%d %H:%M:%S')\n"
    text+="*Host:* $(hostname)\n\n"
    text+="*Details:*\n${message}"
    
    curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
        -d "chat_id=${ADMIN_CHAT_ID}" \
        -d "text=${text}" \
        -d "parse_mode=Markdown" > /dev/null
}

get_rotation_stats() {
    local stats=""
    
    for log_file in "${LOG_FILES[@]}"; do
        local log_path="${LOG_DIR}/${log_file}"
        local size_mb=$(get_file_size_mb "$log_path")
        local rotated_count=$(find "$LOG_DIR" -name "${log_file}.*" 2>/dev/null | wc -l)
        
        stats+="• ${log_file}: ${size_mb}MB (${rotated_count} rotated)\n"
    done
    
    echo -e "$stats"
}

# ==================== MAIN EXECUTION ====================

main() {
    log_message "==================== LOG ROTATION STARTED ===================="
    
    # Check if log directory exists
    if [ ! -d "$LOG_DIR" ]; then
        log_message "Creating log directory: $LOG_DIR"
        mkdir -p "$LOG_DIR"
    fi
    
    # Rotate each log file
    for log_file in "${LOG_FILES[@]}"; do
        rotate_single_log "$log_file"
    done
    
    # Clean up old logs
    cleanup_old_logs
    
    # Archive old logs (if enabled)
    archive_old_logs
    
    # Check disk space
    check_disk_space
    
    # Get rotation stats
    stats=$(get_rotation_stats)
    log_message "Rotation statistics:\n$stats"
    
    # Send notification (if enabled)
    if [ "$ENABLE_NOTIFICATIONS" = true ]; then
        send_notification "Log Rotation Completed" "$stats"
    fi
    
    log_message "==================== LOG ROTATION COMPLETED ===================="
}

# Run main function
main