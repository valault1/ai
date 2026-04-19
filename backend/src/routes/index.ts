// backend/src/routes/index.ts
import { Router } from 'express';
import exampleItems from './exampleItems';
import stocksRouter from './stocks';

const router: Router = Router();

router.use('/example-items', exampleItems);
router.use('/stocks', stocksRouter);

export { router as routes };
