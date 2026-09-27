'use client';

import { Search, SlidersHorizontal } from 'lucide-react';
import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { AdminBackground } from '@/components/admin/AdminBackground';
import { AdminHeader } from '@/components/admin/AdminHeader';
import api from '@/services/api';

interface AdminUser {
  id: string;
  firstName: string;
  lastName: string;
  email: string;
  tier: number;
  status: 'active' | 'suspended';
}

type StatusFilter = 'all' | 'active' | 'suspended';

export default function AdminUsersPage() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [query, setQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [showFilter, setShowFilter] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get('/admin/users')
      .then((res) => setUsers(res.data.data))
      .catch(() => setUsers([]))
      .finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(
    () =>
      users
        .filter((u) => statusFilter === 'all' || u.status === statusFilter)
        .filter((u) =>
          `${u.firstName} ${u.lastName} ${u.email}`
            .toLowerCase()
            .includes(query.toLowerCase()),
        ),
    [users, query, statusFilter],
  );

  return (
    <AdminBackground>
      <AdminHeader
        title="Users"
        rightSlot={
          <button
            type="button"
            aria-label="Filter"
            onClick={() => setShowFilter((v) => !v)}
            className="text-[var(--color-primary)]"
          >
            <SlidersHorizontal className="h-6 w-6" />
          </button>
        }
      />

      <div className="px-6">
        <div className="mb-3 flex items-center gap-2 rounded-full bg-white/10 px-4 py-2">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search"
            className="w-full bg-transparent text-[var(--color-light)] placeholder:text-white/40 focus:outline-none"
          />
          <Search className="h-5 w-5 text-white/40" />
        </div>

        {showFilter && (
          <div className="mb-4 flex gap-2">
            {(['all', 'active', 'suspended'] as StatusFilter[]).map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => setStatusFilter(s)}
                className={`rounded-full px-4 py-1.5 text-sm capitalize ${
                  statusFilter === s
                    ? 'bg-[var(--color-primary)] text-[var(--color-dark)]'
                    : 'bg-white/10 text-[var(--color-light)]'
                }`}
              >
                {s}
              </button>
            ))}
          </div>
        )}

        {loading && <p className="text-white/50">Loading…</p>}
        {!loading && filtered.length === 0 && (
          <p className="text-white/50">No users found.</p>
        )}

        <div className="flex flex-col gap-3 pb-8">
          {filtered.map((u) => (
            <Link
              key={u.id}
              href={`/admin/users/${u.id}`}
              className="flex items-center justify-between rounded-2xl bg-[rgba(var(--color-primary-rgb),0.1)] px-4 py-3 transition-colors hover:bg-[rgba(var(--color-primary-rgb),0.18)]"
            >
              <div className="flex items-center gap-3">
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-[rgba(var(--color-primary-rgb),0.3)] text-sm font-semibold text-[var(--color-primary)]">
                  {u.firstName.charAt(0)}
                  {u.lastName.charAt(0)}
                </div>
                <div>
                  <p className="font-semibold text-[var(--color-light)]">
                    {u.firstName} {u.lastName}
                  </p>
                  <span className="mt-1 inline-block rounded-full bg-white/10 px-2 py-0.5 text-xs text-white/60">
                    Tier {u.tier}
                  </span>
                </div>
              </div>
              <span
                className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide ${
                  u.status === 'active'
                    ? 'bg-[rgba(var(--color-primary-rgb),0.2)] text-[var(--color-primary)]'
                    : 'bg-red-500/15 text-red-400'
                }`}
              >
                {u.status === 'active' ? 'Active' : 'Suspended'}
              </span>
            </Link>
          ))}
        </div>
      </div>
    </AdminBackground>
  );
}
