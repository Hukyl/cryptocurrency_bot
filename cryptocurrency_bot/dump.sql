BEGIN TRANSACTION;
CREATE TABLE currency_predictions(
                    id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
                    user_id INTEGER,
                    iso_from VARCHAR(5),
                    iso_to VARCHAR(5),
                    value DOUBLE,
                    up_to_date DATETIME,
                    is_by_experts BOOLEAN DEFAULT FALSE,
                    real_value DOUBLE DEFAULT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
            );
CREATE TABLE predictions_reactions(
                pred_id INTEGER,
                user_id INTEGER,
                reaction BOOLEAN,
                FOREIGN KEY (pred_id) REFERENCES currency_predictions(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
CREATE TABLE sessions(
                user_id INTEGER NOT NULL,
                free_notifications_count TINYINT DEFAULT 10,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE(user_id) ON CONFLICT REPLACE
            );
DELETE FROM "sqlite_sequence";
CREATE TABLE users( 
                    id INTEGER NOT NULL,
                    is_active BOOLEAN DEFAULT 0,
                    is_pro DATETIME DEFAULT FALSE, 
                    is_staff BOOLEAN DEFAULT 0,
                    to_notify_by_experts BOOLEAN DEFAULT 1,
                    timezone TINYINT DEFAULT 0 CHECK (
                        timezone in (
                            -11, -10, -9, -8, -7, -6, -5, -4, -3, -2, -1, 
                            0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12
                        )
                    ),
                    language VARCHAR(2) DEFAULT "en" CHECK (LENGTH(language) IN (2, 3)), 
                    UNIQUE(id) ON CONFLICT REPLACE
                );
CREATE TABLE users_rates( 
                    user_id INTEGER NOT NULL,
                    iso VARCHAR(5),
                    value DOUBLE DEFAULT 0,
                    percent_delta REAL DEFAULT 1,
                    check_times LIST,
                    UNIQUE(user_id, iso) ON CONFLICT REPLACE,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );
COMMIT;
