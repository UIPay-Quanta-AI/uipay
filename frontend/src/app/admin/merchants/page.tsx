'use client';

import { Search } from 'lucide-react';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import { AdminBackground } from '@/components/admin/AdminBackground';
import { AdminHeader } from '@/components/admin/AdminHeader';
import api from '@/services/api';

interface Merchant {
  id: string;
  businessName: string;
  category: string;
  status: 'pending' | 'approved' | 'rejected';
  user: { firstName: string; lastName: string; email: string };
}

type Tab = 'pending' | 'approved';

export default function AdminMerchantsPage() {
  const [tab, setTab] = useState<Tab>('pending');
  const [merchants, setMerchants] = useState<Merchant[]>([]);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api
      .get(`/admin/merchants?status=${tab}`)
      .then((res) => setMerchants(res.data.data))
      .catch(() => setMerchants([]))
      .finally(() => setLoading(false));
  }, [tab]);

  const filtered = merchants.filter((m) =>
    m.businessName.toLowerCase().includes(query.toLowerCase()),
  );

  return (
    <AdminBackground>
      <AdminHeader title="Merchants" />

      <div className="px-6">
        <div className="mb-4 flex overflow-hidden rounded-xl bg-white/5">
          <TabButton active={tab === 'pending'} onClick={() => setTab('pending')}>
            Pending
          </TabButton>
          <TabButton active={tab === 'approved'} onClick={() => setTab('approved')}>
            Approved
          </TabButton>
        </div>

        <div className="mb-4 flex items-center gap-2 rounded-full bg-white/10 px-4 py-2">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search"
            className="w-full bg-transparent text-[var(--color-light)] placeholder:text-white/40 focus:outline-none"
          />
          <Search className="h-5 w-5 text-white/40" />
        </div>

        {loading && <p className="text-white/50">Loading…</p>}

        {!loading && filtered.length === 0 && (
          <p className="text-white/50">No {tab} merchant applications.</p>
        )}

        <div className="flex flex-col gap-3 pb-8">
          {filtered.map((merchant) => (
            <Link
              key={merchant.id}
              href={`/admin/merchants/${merchant.id}`}
              className="flex items-center gap-3 rounded-2xl bg-[rgba(var(--color-primary-rgb),0.1)] px-4 py-3 transition-colors hover:bg-[rgba(var(--color-primary-rgb),0.18)]"
            >
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-[rgba(var(--color-primary-rgb),0.3)] text-lg font-bold text-[var(--color-primary)]">
                {merchant.businessName.charAt(0).toUpperCase()}
              </div>
              <div>
                <p className="font-semibold uppercase text-[var(--color-light)]">
                  {merchant.businessName}
                </p>
                <p className="text-sm text-white/50">{merchant.category}</p>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </AdminBackground>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex-1 py-3 text-sm font-semibold uppercase tracking-wide ${
        active
          ? 'bg-white/10 text-[var(--color-primary)]'
          : 'text-[var(--color-light)]'
      }`}
    >
      {children}
    </button>
  );
}
