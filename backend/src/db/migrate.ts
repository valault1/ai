// backend/src/db/migrate.ts
import db from './connection';
import fs from 'fs';
import path from 'path';

export function runMigrations(): void {
  // Create migrations tracking table if it doesn't exist
  db.exec(`
    CREATE TABLE IF NOT EXISTS _migrations (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL UNIQUE,
      applied_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
  `);

  const migrationsDir = path.join(__dirname, 'migrations');
  const files = fs.readdirSync(migrationsDir)
    .filter(f => f.endsWith('.sql'))
    .sort(); // Lexicographic sort — numbering prefix ensures correct order

  const applied = new Set(
    db.query('SELECT name FROM _migrations').all().map((r: any) => r.name)
  );

  for (const file of files) {
    if (!applied.has(file)) {
      const sql = fs.readFileSync(path.join(migrationsDir, file), 'utf-8');
      
      const transaction = db.transaction(() => {
        db.exec(sql);
        db.query('INSERT INTO _migrations (name) VALUES (?)').run(file);
      });
      transaction();
      
      console.log(`Applied migration: ${file}`);
    }
  }
}
