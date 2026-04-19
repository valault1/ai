// frontend/src/pages/HomePage.tsx
import { useState, useEffect } from 'react';
import { api } from '../api/client';
import type { GetExampleItemsResponse } from 'shared';

export function HomePage() {
  const [data, setData] = useState<GetExampleItemsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get<GetExampleItemsResponse>('/example-items')
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const createTestItem = async () => {
    try {
      await api.post('/example-items', { 
        name: `Test Item ${Math.floor(Math.random() * 1000)}`,
        description: 'Auto-generated item for testing'
      });
      // Refresh the list
      const newData = await api.get<GetExampleItemsResponse>('/example-items');
      setData(newData);
    } catch (e: any) {
      setError(e.message);
    }
  };

  if (loading) return <div className="p-4 text-gray-500">Loading initial state...</div>;
  if (error) return <div className="p-4 text-red-600 bg-red-50 border border-red-200 rounded">Error: {error}</div>;

  return (
    <div className="max-w-4xl mx-auto p-6 font-sans">
      <div className="flex items-center justify-between mb-6 border-b pb-4">
        <h1 className="text-3xl font-bold text-gray-800">Example Items</h1>
        <button 
          onClick={createTestItem}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition"
        >
          Add Item
        </button>
      </div>
      <p className="text-gray-600 mb-6 bg-gray-50 p-3 rounded">
        Total Items Available: <strong className="text-gray-900">{data?.total}</strong>
      </p>
      {data?.items.length === 0 ? (
        <div className="p-8 text-center text-gray-500 bg-gray-50 border border-dashed rounded">
          No items found. Click 'Add Item' to create one.
        </div>
      ) : (
        <ul className="space-y-3">
          {data?.items.map((item, id) => (
            <li key={item.id || id} className="p-4 bg-white border border-gray-200 rounded shadow-sm hover:shadow transition">
              <span className="font-semibold text-lg text-gray-900 block">{item.name}</span>
              {item.description && (
                <p className="text-sm text-gray-500 mt-1">{item.description}</p>
              )}
              <div className="mt-2 text-xs text-gray-400">ID: {item.id} • Created: {new Date(item.created_at).toLocaleString()}</div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
