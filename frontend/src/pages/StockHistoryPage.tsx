import { useState, useEffect, useRef } from 'react';
import { createChart, ColorType, AreaSeries } from 'lightweight-charts';
import type { IChartApi, ISeriesApi } from 'lightweight-charts';
import { api } from '../api/client';
import type { GetStockHistoryResponse } from 'shared';

export function StockHistoryPage() {
  const [symbol, setSymbol] = useState('VOO');
  
  const defaultEnd = new Date();
  const defaultStart = new Date();
  defaultStart.setFullYear(defaultStart.getFullYear() - 1);
  
  const [start, setStart] = useState(defaultStart.toISOString().split('T')[0]);
  const [end, setEnd] = useState(defaultEnd.toISOString().split('T')[0]);
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<{ time: string; value: number }[]>([]);
  const [visibleReturn, setVisibleReturn] = useState<number | null>(null);
  const [annualizedReturn, setAnnualizedReturn] = useState<number | null>(null);

  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Area"> | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      // Fetch 25 years of data so the user can easily pan back historically.
      // The start and end inputs will be used to constrain the INITIAL viewing window.
      const fetchStart = '2000-01-01';
      const fetchEnd = new Date().toISOString().split('T')[0];
      const response = await api.get<GetStockHistoryResponse>(`/stocks/history?symbol=${symbol}&start=${fetchStart}&end=${fetchEnd}`);
      setData(response.data);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch data');
    } finally {
      setLoading(false);
    }
  };

  const setTimeRange = (rangeType: string) => {
    if (!data.length) return;
    
    const endObj = new Date(data[data.length - 1].time);
    const startObj = new Date(endObj);
    
    if (rangeType === '1W') startObj.setDate(startObj.getDate() - 7);
    else if (rangeType === '1M') startObj.setMonth(startObj.getMonth() - 1);
    else if (rangeType === '3M') startObj.setMonth(startObj.getMonth() - 3);
    else if (rangeType === '1Y') startObj.setFullYear(startObj.getFullYear() - 1);
    else if (rangeType === '5Y') startObj.setFullYear(startObj.getFullYear() - 5);
    else if (rangeType === '10Y') startObj.setFullYear(startObj.getFullYear() - 10);
    else if (rangeType === 'MAX') {
      startObj.setTime(new Date(data[0].time).getTime());
    }
    
    const startStr = startObj.toISOString().split('T')[0];
    const endStr = endObj.toISOString().split('T')[0];
    
    let validStart = data.find(d => d.time >= startStr)?.time || data[0].time;
    let validEnd = [...data].reverse().find(d => d.time <= endStr)?.time || data[data.length - 1].time;
    
    if (rangeType === 'MAX') {
      validStart = data[0].time;
    }
    
    setStart(validStart);
    setEnd(validEnd);
    
    chartRef.current?.timeScale().setVisibleRange({
      from: validStart as any,
      to: validEnd as any,
    });
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Initialize and update chart
  useEffect(() => {
    if (!chartContainerRef.current) return;

    if (!chartRef.current) {
      const chart = createChart(chartContainerRef.current, {
        layout: {
          background: { type: ColorType.Solid, color: 'transparent' },
          textColor: '#8A8F98',
          fontFamily: '"Inter", "Geist Sans", system-ui, sans-serif',
        },
        grid: {
          vertLines: { color: 'rgba(255, 255, 255, 0.02)' },
          horzLines: { color: 'rgba(255, 255, 255, 0.02)' },
        },
        rightPriceScale: {
          borderVisible: false,
        },
        timeScale: {
          borderVisible: false,
          timeVisible: true,
          fixRightEdge: true,
        },
        handleScroll: {
          pressedMouseMove: false, // Disable native drag panning
          vertTouchDrag: false,
          horzTouchDrag: false,
        },
        width: chartContainerRef.current.clientWidth,
        height: 500,
      });

      const newSeries = chart.addSeries(AreaSeries, {
        lineColor: '#5E6AD2',
        topColor: 'rgba(94, 106, 210, 0.4)',
        bottomColor: 'rgba(94, 106, 210, 0.0)',
        lineWidth: 2,
      });
      
      chart.timeScale().subscribeVisibleLogicalRangeChange((logicalRange) => {
        if (!logicalRange) return;
        const bars = newSeries.data();
        if (bars.length === 0) return;
        
        const firstIndex = Math.max(0, Math.floor(logicalRange.from));
        const lastIndex = Math.min(bars.length - 1, Math.ceil(logicalRange.to));
        
        if (firstIndex < bars.length && lastIndex >= 0 && firstIndex <= lastIndex) {
          const startPoint = bars[firstIndex] as any;
          const endPoint = bars[lastIndex] as any;
          const startVal = startPoint.value;
          const endVal = endPoint.value;
          if (startVal > 0) {
            setVisibleReturn(((endVal - startVal) / startVal) * 100);
            
            const startMs = new Date(startPoint.time).getTime();
            const endMs = new Date(endPoint.time).getTime();
            const years = (endMs - startMs) / (1000 * 60 * 60 * 24 * 365.25);
            
            if (years > 0) {
              setAnnualizedReturn((Math.pow(endVal / startVal, 1 / years) - 1) * 100);
            } else {
              setAnnualizedReturn(null);
            }
          }
        }
      });

      chartRef.current = chart;
      seriesRef.current = newSeries;

      let isZoomDragging = false;
      let startX: number | null = null;
      let endX: number | null = null;

      const drawZoomBox = (start: number, end: number) => {
        let box = document.getElementById('chart-zoom-box');
        if (!box) {
           box = document.createElement('div');
           box.id = 'chart-zoom-box';
           box.style.position = 'absolute';
           box.style.backgroundColor = 'rgba(94, 106, 210, 0.2)';
           box.style.border = '1px solid rgba(94, 106, 210, 0.5)';
           box.style.top = '0';
           box.style.bottom = '0';
           box.style.zIndex = '10';
           box.style.pointerEvents = 'none';
           chartContainerRef.current?.appendChild(box);
        }
        const left = Math.min(start, end);
        const width = Math.abs(start - end);
        box.style.left = `${left}px`;
        box.style.width = `${width}px`;
        box.style.display = 'block';
      };

      const clearZoomBox = () => {
        const box = document.getElementById('chart-zoom-box');
        if (box) box.style.display = 'none';
      };

      const handleMouseDown = (e: MouseEvent) => {
        isZoomDragging = true;
        startX = e.offsetX;
        endX = e.offsetX;
      };
      
      const handleMouseMove = (e: MouseEvent) => {
        if (!isZoomDragging || startX === null) return;
        endX = e.offsetX;
        drawZoomBox(startX, endX);
      };

      const handleMouseUp = () => {
        if (!isZoomDragging || startX === null || endX === null) return;
        isZoomDragging = false;
        clearZoomBox();
        const diff = Math.abs(endX - startX);
        if (diff > 10) {
           const ts = chart.timeScale();
           const l1 = ts.coordinateToLogical(startX);
           const l2 = ts.coordinateToLogical(endX);
           if (l1 !== null && l2 !== null) {
              const from = Math.min(l1, l2);
              const to = Math.max(l1, l2);
              ts.setVisibleLogicalRange({ from, to });
           }
        }
        startX = null;
        endX = null;
      };

      const handleMouseLeave = () => {
         if (isZoomDragging) {
           handleMouseUp();
         }
      };

      if (chartContainerRef.current) {
        chartContainerRef.current.addEventListener('mousedown', handleMouseDown);
        chartContainerRef.current.addEventListener('mousemove', handleMouseMove);
        chartContainerRef.current.addEventListener('mouseup', handleMouseUp);
        chartContainerRef.current.addEventListener('mouseleave', handleMouseLeave);
      }

      const handleResize = () => {
        if (chartContainerRef.current && chartRef.current) {
          chartRef.current.applyOptions({ width: chartContainerRef.current.clientWidth });
        }
      };
      window.addEventListener('resize', handleResize);
      return () => {
        window.removeEventListener('resize', handleResize);
        if (chartContainerRef.current) {
          chartContainerRef.current.removeEventListener('mousedown', handleMouseDown);
          chartContainerRef.current.removeEventListener('mousemove', handleMouseMove);
          chartContainerRef.current.removeEventListener('mouseup', handleMouseUp);
          chartContainerRef.current.removeEventListener('mouseleave', handleMouseLeave);
        }
        chart.remove();
        chartRef.current = null;
      };
    }
  }, []);

  useEffect(() => {
    if (seriesRef.current && data.length > 0) {
      // Sort data to ensure it's ascending chronologically
      const sorted = [...data].sort((a, b) => new Date(a.time).getTime() - new Date(b.time).getTime());
      
      seriesRef.current.setData(sorted as any);
      
      let validStart = sorted.find(d => d.time >= start)?.time || sorted[0].time;
      let validEnd = [...sorted].reverse().find(d => d.time <= end)?.time || sorted[sorted.length - 1].time;

      chartRef.current?.timeScale().setVisibleRange({
        from: validStart as any,
        to: validEnd as any,
      });
    }
  }, [data]);

  return (
    <div className="flex flex-col gap-8 max-w-6xl mx-auto w-full h-full font-sans">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h2 className="text-3xl font-semibold tracking-tight text-[#EDEDEF]">Stock History</h2>
          <p className="text-[#8A8F98] text-sm mt-1">Interactive historical analyzer.</p>
        </div>
        
        {/* Controls */}
        <div className="flex flex-wrap items-center gap-3 bg-white/[0.03] p-2 rounded-xl border border-white/[0.06]">
          <div className="flex flex-col">
            <label className="text-[10px] uppercase tracking-widest text-[#8A8F98] px-1 mb-1">Symbol</label>
            <input 
              value={symbol}
              onChange={(e) => setSymbol(e.target.value.toUpperCase())}
              className="bg-[#020203] border border-white/10 rounded-lg px-3 py-1.5 text-sm text-[#EDEDEF] focus:outline-none focus:border-[#5E6AD2]"
            />
          </div>
          <div className="flex flex-col">
            <label className="text-[10px] uppercase tracking-widest text-[#8A8F98] px-1 mb-1">Start Date</label>
            <input 
              type="date"
              value={start}
              onChange={(e) => setStart(e.target.value)}
              className="bg-[#020203] border border-white/10 rounded-lg px-3 py-1.5 text-sm text-[#EDEDEF] focus:outline-none focus:border-[#5E6AD2]"
            />
          </div>
          <div className="flex flex-col">
            <label className="text-[10px] uppercase tracking-widest text-[#8A8F98] px-1 mb-1">End Date</label>
            <input 
              type="date"
              value={end}
              onChange={(e) => setEnd(e.target.value)}
              className="bg-[#020203] border border-white/10 rounded-lg px-3 py-1.5 text-sm text-[#EDEDEF] focus:outline-none focus:border-[#5E6AD2]"
            />
          </div>
          <button 
            onClick={fetchData}
            disabled={loading}
            className="self-end px-4 py-1.5 bg-[#5E6AD2] hover:bg-[#6872D9] active:scale-[0.98] text-white rounded-lg text-sm transition-all shadow-[0_0_15px_rgba(94,106,210,0.3)] disabled:opacity-50"
          >
            {loading ? 'Loading...' : 'Load'}
          </button>
        </div>
      </div>
      
      <div className="flex-1 bg-gradient-to-b from-white/[0.08] to-white/[0.02] border border-white/[0.06] rounded-2xl p-6 relative flex flex-col shadow-[0_10px_30px_rgba(0,0,0,0.5)]">
        <div className="flex items-center justify-between mb-4 z-10">
          <h3 className="text-xl font-semibold tracking-tight text-[#EDEDEF]">{symbol} Performance</h3>
          {visibleReturn !== null && (
            <div className="flex gap-4">
              <div className="flex items-center gap-2 bg-[#020203]/50 px-3 py-1.5 rounded-lg border border-white/10">
                <span className="text-sm text-[#8A8F98]">Window Return:</span>
                <span className={`text-lg font-mono ${visibleReturn >= 0 ? 'text-green-400 drop-shadow-[0_0_8px_rgba(74,222,128,0.4)]' : 'text-red-400 drop-shadow-[0_0_8px_rgba(248,113,113,0.4)]'}`}>
                  {visibleReturn >= 0 ? '+' : ''}{visibleReturn.toFixed(2)}%
                </span>
              </div>
              {annualizedReturn !== null && (
                <div className="flex items-center gap-2 bg-[#020203]/50 px-3 py-1.5 rounded-lg border border-white/10">
                  <span className="text-sm text-[#8A8F98]">Annualized:</span>
                  <span className={`text-lg font-mono ${annualizedReturn >= 0 ? 'text-green-400 drop-shadow-[0_0_8px_rgba(74,222,128,0.4)]' : 'text-red-400 drop-shadow-[0_0_8px_rgba(248,113,113,0.4)]'}`}>
                    {annualizedReturn >= 0 ? '+' : ''}{annualizedReturn.toFixed(2)}%
                  </span>
                </div>
              )}
            </div>
          )}
        </div>
        
        {error && (
          <div className="text-red-400 text-sm mb-4 bg-red-900/20 p-3 rounded-lg border border-red-500/30">
            {error}
          </div>
        )}
        
        {/* Dynamic Chart Container */}
        <div className="flex-1 w-full relative min-h-[400px]">
          <div ref={chartContainerRef} className="absolute inset-0 w-full h-full" />
        </div>

        {/* Quick Ranges */}
        <div className="flex justify-center mt-4 gap-2 border-t border-white/[0.06] pt-4 relative z-10 shrink-0">
          {['1W', '1M', '3M', '1Y', '5Y', '10Y', 'MAX'].map((range) => (
            <button
              key={range}
              onClick={() => setTimeRange(range)}
              className="text-xs font-semibold px-4 py-1.5 rounded-lg text-[#8A8F98] hover:text-[#EDEDEF] hover:bg-white/[0.05] transition-colors focus:outline-none focus:ring-2 focus:ring-[#5E6AD2]/50"
            >
              {range}
            </button>
          ))}
        </div>
        
        {loading && (
          <div className="absolute inset-0 bg-[#0a0a0c]/50 backdrop-blur-sm z-20 flex items-center justify-center rounded-2xl">
            <div className="text-[#5E6AD2] animate-pulse font-medium">Fetching Data...</div>
          </div>
        )}
      </div>
    </div>
  );
}
