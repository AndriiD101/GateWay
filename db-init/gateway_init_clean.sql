-- ==========================================
-- GATEWAY DATABASE INIT
-- ==========================================
CREATE DATABASE IF NOT EXISTS gateway_db;
USE gateway_db;

-- ==========================================
-- USERS TABLE
-- ==========================================
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================
-- CHAT MESSAGES TABLE (Gateway-specific)
-- ==========================================
CREATE TABLE IF NOT EXISTS chat_messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    role ENUM('user', 'assistant') NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ==========================================
-- DEFAULT ADMIN USER
-- Password: admin123  
-- ==========================================
INSERT IGNORE INTO users (username, password_hash, role)
VALUES (
    'admin',
    '$2b$12$rP5TjgdKK1GBr60ug.1o8enwTWpIgOtUteR5vozsvqspbW3D7CZB.',
    'admin'
);

