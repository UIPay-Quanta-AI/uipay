'use client';

import { useParams } from 'next/navigation';
import { useEffect, useState } from 'react';
import { AdminBackground } from '@/components/admin/AdminBackground';
import { AdminHeader } from '@/components/admin/AdminHeader';
import api from '@/services/api';

interface ActivityItem {
  id: string;
  amount: string;
  method: string;
  status: string;
  senderName: string;
  recipientName: string;
  createdAt: string;
}

export default function AdminUserActivityPage() {
  const { id } = useParams<{ id: string }>();
  const [items, setItems] = useState<ActivityItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get(`/admin/users/${id}/activity`)
      .then((res) => setItems(res.data.data))
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, [id]);

  return (
    <AdminBackground>
      <AdminHeader title="Activity Log" />

      <div className="px-6">
        {loading && <p className="text-white/50">Loading…</p>}
        {!loading && items.length === 0 && (
          <p className="text-white/50">No transaction activity yet.</p>
        )}

        <div className="flex flex-col">
          {items.map((item) => (
            <div
              key={item.id}
              className="flex items-center justify-between border-b border-white/10 py-4"
            >
              <div>
                <p className="font-semibold text-[var(--color-light)]">
                  {item.senderName} → {item.recipientName}
                </p>
                <p className="text-sm text-white/50 capitalize">
                  {item.method.replace('_', ' ')} · {item.status}
                </p>
              </div>
              <div className="text-right">
                <p className="text-[var(--color-light)]">
                  ₦{Number(item.amount).toLocaleString()}
                </p>
                <p className="text-sm text-white/50">
                  {new Date(item.createdAt).toLocaleString('en-GB', {
                    hour: '2-digit',
                    minute: '2-digit',
                    day: 'numeric',
                    month: 'short',
                  })}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </AdminBackground>
  );
}
