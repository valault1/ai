import yahooFinance from 'yahoo-finance2';

async function test() {
  const result = await yahooFinance.historical('VOO', {
    period1: '2025-04-10',
    period2: '2025-04-18'
  });
  console.log(result);
}

test();
