// backend/src/db/connection.ts
import { Database } from 'bun:sqlite';
import path from 'path';

const DB_PATH = path.join(__dirname, '../../data/app.db');

// Single connection, reused everywhere. bun:sqlite is synchronous
// and handles concurrent access within a single process fine.
const db = new Database(DB_PATH);

// Enable WAL mode for better read performance
db.exec('PRAGMA journal_mode = WAL;');
// Enable foreign keys (off by default in SQLite)
db.exec('PRAGMA foreign_keys = ON;');

export default db;
