'use client';

import { AlertTriangle, ChevronDown, Phone, Send } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { BackButton } from '@/components/BackButton';
import { GlowBackground } from '@/components/GlowBackground';
import api, { getApiErrorMessage } from '@/services/api';
import { useAuthHydration, useAuthStore } from '@/store/auth';

const FAQ = [
  {
    question: 'How do I upgrade my tier?',
    answer:
      "Account tiers aren't set up yet. For now, completing your KYC (BVN or NIN, from the Complete Your KYC banner on your dashboard) is what verifies your identity - tiered limits will build on top of that once they're introduced.",
  },
  {
    question: 'How do I create a merchant account?',
    answer:
      'Apply from your merchant application (businessName + category). An admin reviews and approves it - once approved, you can register NFC tags and generate QR codes to accept payments.',
  },
  {
    question: 'How do I change my account PIN?',
    answer:
      "Go to More > Settings > Security Settings > Change Transaction PIN. You'll need to confirm your current PIN first.",
  },
];

export default function SupportPage() {
  const router = useRouter();
  const hasHydrated = useAuthHydration();
  const accessToken = useAuthStore((state) => state.accessToken);

  const [chatMessage, setChatMessage] = useState('');
  const [chatSent, setChatSent] = useState(false);
  const [isSendingChat, setIsSendingChat] = useState(false);

  const [showIssueForm, setShowIssueForm] = useState(false);
  const [issueMessage, setIssueMessage] = useState('');
  const [issueSent, setIssueSent] = useState(false);
  const [isSendingIssue, setIsSendingIssue] = useState(false);

  const [openFaq, setOpenFaq] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (hasHydrated && !accessToken) {
      router.replace('/signin');
    }
  }, [hasHydrated, accessToken, router]);

  const handleSendChat = async () => {
    if (!chatMessage.trim()) return;

    setError(null);
    setIsSendingChat(true);
    try {
      await api.post('/support/messages', {
        type: 'chat',
        message: chatMessage.trim(),
      });
      setChatMessage('');
      setChatSent(true);
      setTimeout(() => setChatSent(false), 3000);
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setIsSendingChat(false);
    }
  };

  const handleSendIssue = async () => {
    if (!issueMessage.trim()) return;

    setError(null);
    setIsSendingIssue(true);
    try {
      await api.post('/support/messages', {
        type: 'issue',
        message: issueMessage.trim(),
      });
      setIssueMessage('');
      setShowIssueForm(false);
      setIssueSent(true);
      setTimeout(() => setIssueSent(false), 3000);
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setIsSendingIssue(false);
    }
  };

  if (!hasHydrated || !accessToken) return null;

  return (
    <GlowBackground className="flex flex-col px-6 py-10">
      <div className="flex items-center gap-4">
        <BackButton />
        <h1 className="text-xl font-bold text-[var(--color-light)]">
          Support
        </h1>
      </div>

      <div className="animate-rise-in mt-6 rounded-2xl border border-[var(--color-primary)]/50 bg-[rgba(var(--color-primary-rgb),0.1)] p-5">
        <h2 className="text-lg font-bold text-[var(--color-light)]">
          Need Help?
        </h2>
        <div className="mt-3 flex items-center gap-2">
          <input
            value={chatMessage}
            onChange={(event) => setChatMessage(event.target.value)}
            onKeyDown={(event) => event.key === 'Enter' && handleSendChat()}
            placeholder="Chat with us"
            className="flex-1 rounded-full bg-[rgba(var(--color-primary-rgb),0.15)] px-4 py-3 text-[var(--color-light)] placeholder:text-white/40 focus:outline-none"
          />
          <button
            type="button"
            onClick={handleSendChat}
            disabled={!chatMessage.trim() || isSendingChat}
            aria-label="Send"
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-[var(--color-primary)] text-[var(--color-dark)] disabled:opacity-40"
          >
            <Send className="h-5 w-5" />
          </button>
        </div>
        {chatSent && (
          <p className="animate-fade-slide-in mt-2 text-sm text-[var(--color-primary)]">
            Message sent - we&apos;ll get back to you by email.
          </p>
        )}
      </div>

      <div
        title="Coming soon - no support line set up yet"
        className="mt-4 flex items-center justify-between rounded-2xl bg-[rgba(var(--color-primary-rgb),0.1)] px-5 py-4 opacity-50"
      >
        <span className="text-[var(--color-light)]">Contact Support !!</span>
        <Phone className="h-5 w-5 text-[var(--color-primary)]" />
      </div>

      <h2 className="mt-8 text-lg font-bold text-[var(--color-light)]">
        FAQ
      </h2>
      <div className="mt-2 flex flex-col">
        {FAQ.map((item, index) => (
          <div key={item.question} className="border-b border-white/10 py-4">
            <button
              type="button"
              onClick={() => setOpenFaq(openFaq === index ? null : index)}
              className="flex w-full items-center justify-between text-left text-[var(--color-light)]"
            >
              {item.question}
              <ChevronDown
                className={`h-5 w-5 shrink-0 text-white/40 transition-transform ${
                  openFaq === index ? 'rotate-180' : ''
                }`}
              />
            </button>
            {openFaq === index && (
              <p className="animate-fade-slide-in mt-3 text-sm text-white/60">
                {item.answer}
              </p>
            )}
          </div>
        ))}
      </div>

      {error && <p className="mt-4 text-sm text-red-400">{error}</p>}

      <div className="mt-8 mb-6">
        {showIssueForm ? (
          <div className="flex flex-col gap-3 rounded-2xl border border-red-400/40 p-4">
            <textarea
              value={issueMessage}
              onChange={(event) => setIssueMessage(event.target.value)}
              placeholder="Describe the issue..."
              rows={3}
              className="rounded-xl border border-white/20 bg-transparent px-4 py-3 text-[var(--color-light)] placeholder:text-white/30 focus:border-red-400 focus:outline-none"
            />
            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => setShowIssueForm(false)}
                className="flex-1 rounded-full bg-white/10 py-3 text-sm font-semibold text-[var(--color-light)]"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSendIssue}
                disabled={!issueMessage.trim() || isSendingIssue}
                className="flex-1 rounded-full bg-red-500 py-3 text-sm font-semibold text-white disabled:opacity-40"
              >
                {isSendingIssue ? 'Sending...' : 'Submit'}
              </button>
            </div>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => setShowIssueForm(true)}
            className="flex w-full items-center justify-center gap-2 rounded-full border border-red-400/60 py-4 font-semibold text-red-400"
          >
            <AlertTriangle className="h-5 w-5" />
            Report Issue
          </button>
        )}
        {issueSent && (
          <p className="animate-fade-slide-in mt-2 text-center text-sm text-[var(--color-primary)]">
            Thanks - your report was received.
          </p>
        )}
      </div>
    </GlowBackground>
  );
}
