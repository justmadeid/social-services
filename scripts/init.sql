-- Initialize Twitter Scraper Database
-- This script creates the necessary tables for the application

CREATE DATABASE IF NOT EXISTS twitter_scraper CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE twitter_scraper;

-- Twitter Credentials Table
CREATE TABLE IF NOT EXISTS twitter_credentials (
    id INT PRIMARY KEY AUTO_INCREMENT,
    credential_name VARCHAR(100) NOT NULL UNIQUE,
    username VARCHAR(255) NOT NULL,
    encrypted_password TEXT NOT NULL,
    salt VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_login_attempt TIMESTAMP NULL,
    login_success_count INT DEFAULT 0,
    login_failure_count INT DEFAULT 0,
    INDEX idx_credential_name (credential_name),
    INDEX idx_is_active (is_active)
);

-- Scraping Logs Table (Optional - for audit trail)
CREATE TABLE IF NOT EXISTS scraping_logs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    task_id VARCHAR(255) NOT NULL UNIQUE,
    operation_type ENUM('search_user', 'following', 'followers', 'timeline') NOT NULL,
    parameters JSON NOT NULL,
    status ENUM('PENDING', 'PROCESSING', 'SUCCESS', 'FAILURE') DEFAULT 'PENDING',
    result_size INT NULL,
    execution_time_seconds DECIMAL(10,3) NULL,
    error_message TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    INDEX idx_task_id (task_id),
    INDEX idx_operation_type (operation_type),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
);

-- Insert default admin user (optional)
-- INSERT INTO twitter_credentials (credential_name, username, encrypted_password, salt)
-- VALUES ('default', 'your_twitter_username', 'encrypted_password_here', 'salt_here');
