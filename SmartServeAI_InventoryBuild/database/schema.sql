CREATE DATABASE IF NOT EXISTS smartserve_db
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE smartserve_db;

CREATE TABLE IF NOT EXISTS forecasts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    forecast_date DATE NOT NULL,
    item VARCHAR(100) NOT NULL,
    predicted_demand DECIMAL(10,2) NOT NULL,
    recommended_production INT NOT NULL,
    waste_risk VARCHAR(20),
    weather VARCHAR(50),
    event VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_forecast_date (forecast_date),
    INDEX idx_forecast_item (item)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS sales_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sale_date DATE NOT NULL,
    item VARCHAR(100) NOT NULL,
    quantity_sold INT NOT NULL,
    prepared_quantity INT DEFAULT 0,
    weather VARCHAR(50),
    event VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_sales_date (sale_date),
    INDEX idx_sales_item (item)
) ENGINE=InnoDB;


CREATE TABLE IF NOT EXISTS ingredient_inventory (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ingredient VARCHAR(100) NOT NULL UNIQUE,
    stock_quantity DECIMAL(12,3) NOT NULL DEFAULT 0,
    unit VARCHAR(20) NOT NULL,
    unit_cost DECIMAL(12,2) NOT NULL DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS procurement_alerts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    alert_date DATE NOT NULL,
    ingredient VARCHAR(100) NOT NULL,
    required_quantity DECIMAL(12,3) NOT NULL,
    available_quantity DECIMAL(12,3) NOT NULL,
    shortage_quantity DECIMAL(12,3) NOT NULL,
    recommended_order DECIMAL(12,3) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'OPEN',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_procurement_date (alert_date),
    INDEX idx_procurement_status (status)
) ENGINE=InnoDB;
