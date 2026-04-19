// backend/src/index.ts
import express from 'express';
import cors from 'cors';
import { runMigrations } from './db/migrate';
import { routes } from './routes';
import { errorHandler } from './middleware/errorHandler';

const app = express();
const PORT = process.env.PORT || 3002;

// Vite's default port 5173
app.use(cors({ origin: 'http://localhost:5173' }));
app.use(express.json());

// Run migrations on startup
runMigrations();

// Mount all routes
app.use('/api', routes);

// Global error handler
app.use(errorHandler);

app.listen(PORT, () => {
  console.log(`Backend running on http://localhost:${PORT}`);
});
