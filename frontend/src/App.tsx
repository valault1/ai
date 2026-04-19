// frontend/src/App.tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { HomePage } from './pages/HomePage';
import { StockHistoryPage } from './pages/StockHistoryPage';
import { AppLayout } from './components/layout/AppLayout';

export default function App() {
  return (
    <BrowserRouter>
      <AppLayout>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/stocks" element={<StockHistoryPage />} />
          <Route path="/stocks/history" element={<StockHistoryPage />} />
          {/* Add new routes here */}
        </Routes>
      </AppLayout>
    </BrowserRouter>
  );
}
