#!/bin/bash
# telegram-bot/scripts/backup_db.sh
# Estif Bingo 24/7 - Database Backup Script
# Automated backup of PostgreSQL database with rotation

# ==================== CONFIGURATION ====================

# Load environment variables
if [ -f ../.env ]; then
    source ../.env
elif [ -f .env ]; then
    source .env
fi

# Backup directory
BACKUP_DIR="../backups"
DATE=$(date +%Y%m%d_%H%M%S)
WEEKDAY=$(date +%u)
DAY_OF_MONTH=$(date +%d)
MONTH=$(date +%m)
YEAR=$(date +%Y)

# Backup file names
DAILY_BACKUP="${BACKUP_DIR}/backup_daily_${DATE}.sql.gz"
WEEKLY_BACKUP="${BACKUP_DIR}/backup_week_${WEEKDAY}_${DATE}.sql.gz"
MONTHLY_BACKUP="${BACKUP_DIR}/backup_month_${MONTH}_${YEAR}.sql.gz"

# Retention periods (in days)
DAILY_RETENTION=7
WEEKLY_RETENTION=28
MONTHLY_RETENTION=180

# Database connection settings (from DATABASE_URL)
DB_URL="${DATABASE_URL}"

# Log file
LOG_FILE="${BACKUP_DIR}/backup.log"

# ==================== FUNCTIONS ====================

log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

check_prerequisites() {
    # Check if pg_dump is available
    if ! command -v pg_dump &> /dev/null; then
        log_message "ERROR: pg_dump not found. Please install PostgreSQL client."
        exit 1
    fi
    
    # Check if backup directory exists
    if [ ! -d "$BACKUP_DIR" ]; then
        log_message "Creating backup directory: $BACKUP_DIR"
        mkdir -p "$BACKUP_DIR"
    fi
    
    # Check if DATABASE_URL is set
    if [ -z "$DB_URL" ]; then
        log_message "ERROR: DATABASE_URL not set in environment"
        exit 1
    fi
    
    log_message "Prerequisites check passed"
}

create_daily_backup() {
    log_message "Creating daily backup: $DAILY_BACKUP"
    
    # Perform backup with pg_dump
    pg_dump "$DB_URL" | gzip > "$DAILY_BACKUP"
    
    # Check if backup was successful
    if [ $? -eq 0 ] && [ -f "$DAILY_BACKUP" ]; then
        BACKUP_SIZE=$(du -h "$DAILY_BACKUP" | cut -f1)
        log_message "Daily backup completed successfully. Size: $BACKUP_SIZE"
        return 0
    else
        log_message "ERROR: Daily backup failed"
        return 1
    fi
}

create_weekly_backup() {
    # Create weekly backup on Monday (weekday = 1)
    if [ "$WEEKDAY" -eq 1 ]; then
        log_message "Creating weekly backup: $WEEKLY_BACKUP"
        
        cp "$DAILY_BACKUP" "$WEEKLY_BACKUP"
        
        if [ $? -eq 0 ] && [ -f "$WEEKLY_BACKUP" ]; then
            BACKUP_SIZE=$(du -h "$WEEKLY_BACKUP" | cut -f1)
            log_message "Weekly backup completed successfully. Size: $BACKUP_SIZE"
            return 0
        else
            log_message "ERROR: Weekly backup failed"
            return 1
        fi
    else
        log_message "Skipping weekly backup (today is not Monday)"
        return 0
    fi
}

create_monthly_backup() {
    # Create monthly backup on 1st day of month
    if [ "$DAY_OF_MONTH" -eq 1 ]; then
        log_message "Creating monthly backup: $MONTHLY_BACKUP"
        
        cp "$DAILY_BACKUP" "$MONTHLY_BACKUP"
        
        if [ $? -eq 0 ] && [ -f "$MONTHLY_BACKUP" ]; then
            BACKUP_SIZE=$(du -h "$MONTHLY_BACKUP" | cut -f1)
            log_message "Monthly backup completed successfully. Size: $BACKUP_SIZE"
            return 0
        else
            log_message "ERROR: Monthly backup failed"
            return 1
        fi
    else
        log_message "Skipping monthly backup (today is not 1st of month)"
        return 0
    fi
}

rotate_backups() {
    log_message "Rotating old backups..."
    
    # Rotate daily backups (older than DAILY_RETENTION days)
    find "$BACKUP_DIR" -name "backup_daily_*.sql.gz" -type f -mtime +${DAILY_RETENTION} -delete
    DAILY_DELETED=$(find "$BACKUP_DIR" -name "backup_daily_*.sql.gz" -type f -mtime +${DAILY_RETENTION} -print | wc -l)
    
    # Rotate weekly backups (older than WEEKLY_RETENTION days)
    find "$BACKUP_DIR" -name "backup_week_*.sql.gz" -type f -mtime +${WEEKLY_RETENTION} -delete
    WEEKLY_DELETED=$(find "$BACKUP_DIR" -name "backup_week_*.sql.gz" -type f -mtime +${WEEKLY_RETENTION} -print | wc -l)
    
    # Rotate monthly backups (older than MONTHLY_RETENTION days)
    find "$BACKUP_DIR" -name "backup_month_*.sql.gz" -type f -mtime +${MONTHLY_RETENTION} -delete
    MONTHLY_DELETED=$(find "$BACKUP_DIR" -name "backup_month_*.sql.gz" -type f -mtime +${MONTHLY_RETENTION} -print | wc -l)
    
    log_message "Backup rotation completed. Deleted: Daily=$DAILY_DELETED, Weekly=$WEEKLY_DELETED, Monthly=$MONTHLY_DELETED"
}

verify_backup() {
    log_message "Verifying backup integrity..."
    
    # Test if backup file is valid gzip
    if gunzip -t "$DAILY_BACKUP" 2>/dev/null; then
        log_message "Backup verification passed: $DAILY_BACKUP is valid"
        return 0
    else
        log_message "ERROR: Backup verification failed: $DAILY_BACKUP is corrupted"
        return 1
    fi
}

upload_to_cloud() {
    # Optional: Upload to cloud storage (AWS S3, Google Cloud, etc.)
    # Uncomment and configure if needed
    
    # if command -v aws &> /dev/null; then
    #     log_message "Uploading to AWS S3..."
    #     aws s3 cp "$DAILY_BACKUP" s3://your-bucket-name/backups/
    #     if [ $? -eq 0 ]; then
    #         log_message "Upload to S3 completed"
    #     else
    #         log_message "WARNING: Upload to S3 failed"
    #     fi
    # fi
    
    log_message "Cloud upload skipped (not configured)"
}

send_notification() {
    local status=$1
    local message=$2
    
    # Optional: Send notification via Telegram bot
    # Uncomment and configure if needed
    
    # if [ -n "$ADMIN_CHAT_ID" ] && [ -n "$BOT_TOKEN" ]; then
    #     curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
    #         -d "chat_id=${ADMIN_CHAT_ID}" \
    #         -d "text=📁 *Backup Status*\n\nStatus: ${status}\nMessage: ${message}\nTime: $(date)" \
    #         -d "parse_mode=Markdown" > /dev/null
    # fi
    
    log_message "Notification: $status - $message"
}

# ==================== MAIN EXECUTION ====================

main() {
    log_message "==================== BACKUP STARTED ===================="
    
    # Check prerequisites
    check_prerequisites
    
    # Create daily backup
    if create_daily_backup; then
        # Verify backup
        if verify_backup; then
            # Create weekly backup if applicable
            create_weekly_backup
            
            # Create monthly backup if applicable
            create_monthly_backup
            
            # Rotate old backups
            rotate_backups
            
            # Optional: Upload to cloud
            upload_to_cloud
            
            send_notification "✅ SUCCESS" "Daily backup completed successfully"
            log_message "==================== BACKUP COMPLETED ===================="
            exit 0
        else
            send_notification "⚠️ WARNING" "Backup verification failed"
            log_message "==================== BACKUP FAILED (VERIFICATION) ===================="
            exit 1
        fi
    else
        send_notification "❌ FAILED" "Daily backup creation failed"
        log_message "==================== BACKUP FAILED ===================="
        exit 1
    fi
}

# Run main function
main