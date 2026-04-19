import { Router, Request, Response } from 'express';
import YahooFinance from 'yahoo-finance2';
import type { GetStockHistoryResponse, StockHistoryPoint } from 'shared';

const router: Router = Router();
const yf = new YahooFinance();

router.get('/history', async (req: Request, res: Response) => {
  try {
    const symbol = req.query.symbol as string;
    const start = req.query.start as string;
    const end = req.query.end as string;

    if (!symbol || !start || !end) {
      return res.status(400).json({ error: 'Missing symbol, start, or end parameters' });
    }

    const queryOptions = {
      period1: start,
      period2: end,
      interval: '1d' as const,
    };

    const chart = await yf.chart(symbol, queryOptions);
    
    const data: StockHistoryPoint[] = chart.quotes
      .filter((q: any) => q.close !== null)
      .map((q: any) => {
        // q.date is a Date object. Convert to YYYY-MM-DD string
        const dateObj = new Date(q.date);
        const year = dateObj.getFullYear();
        const month = String(dateObj.getMonth() + 1).padStart(2, '0');
        const day = String(dateObj.getDate()).padStart(2, '0');
        return {
          time: `${year}-${month}-${day}`,
          value: q.close as number,
        };
      });

    const response: GetStockHistoryResponse = {
      symbol,
      data
    };

    res.json(response);
  } catch (error: any) {
    console.error('Error fetching stock history:', error);
    res.status(500).json({ error: error.message });
  }
});

export default router;
