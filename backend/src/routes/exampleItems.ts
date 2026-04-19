// backend/src/routes/exampleItems.ts
import { Router } from 'express';
import db from '../db/connection';
import type {
  GetExampleItemsResponse,
  CreateExampleItemRequest,
  CreateExampleItemResponse,
} from 'shared';

const router: Router = Router();

router.get('/', (req, res) => {
  const items = db.query('SELECT * FROM example_items ORDER BY created_at DESC').all();
  const total = db.query('SELECT COUNT(*) as count FROM example_items').get() as any;
  const response: GetExampleItemsResponse = { items: items as any, total: total.count };
  res.json(response);
});

router.post('/', (req, res) => {
  const body = req.body as CreateExampleItemRequest;
  if (!body.name) {
    res.status(400).json({ error: 'name is required' });
    return;
  }
  
  const insert = db.query('INSERT INTO example_items (name, description) VALUES (?, ?)');
  insert.run(body.name, body.description ?? null);
  
  // To get the last insert ID robustly in bun:sqlite (when not using simple .run returns):
  // Since .run() returns { lastInsertRowid, changes }, we can capture it.
  const rowIdResult = db.query('SELECT last_insert_rowid() as id').get() as any;
  const item = db.query('SELECT * FROM example_items WHERE id = ?').get(rowIdResult.id);
  const response: CreateExampleItemResponse = { item: item as any };
  res.status(201).json(response);
});

export default router;
