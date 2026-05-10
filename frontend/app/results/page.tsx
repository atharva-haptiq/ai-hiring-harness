"use client";

import { useState } from "react";
import { rankCandidates, generateOutreach } from "../lib/api";

interface Candidate {
  rank: number;
  name: string;
  email: string;
  score: number;
  reason: string;
  candidate_id?: number;
  id?: number;
}

interface OutreachResult {
  subject: string;
  body: string;
  candidateName: string;
}

export default function ResultsPage() {
  const [jobId, setJobId] = useState("");
  const [candidates, setCandidates] = useState<Candidate[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [outreachLoading, setOutreachLoading] = useState<number | null>(null);
  const [outreachError, setOutreachError] = useState<string | null>(null);
  const [outreachModal, setOutreachModal] = useState<OutreachResult | null>(null);

  async function handleFetch(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setCandidates(null);
    try {
      const result = await rankCandidates(Number(jobId));
      const list: Candidate[] = Array.isArray(result) ? result : result?.candidates ?? result?.results ?? [];
      setCandidates(list);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch rankings.");
    } finally {
      setLoading(false);
    }
  }

  async function handleOutreach(c: Candidate, index: number) {
    const candidateId = c.candidate_id ?? c.id ?? index;
    setOutreachLoading(candidateId);
    setOutreachError(null);
    try {
      const result = await generateOutreach(candidateId, Number(jobId));
      if (!result?.subject || !result?.body) throw new Error("Unexpected response from server.");
      setOutreachModal({ subject: result.subject, body: result.body, candidateName: c.name });
    } catch (err) {
      setOutreachError(err instanceof Error ? err.message : "Failed to generate outreach.");
    } finally {
      setOutreachLoading(null);
    }
  }

  return (
    <div className="min-h-screen bg-linear-to-br from-slate-900 via-slate-800 to-slate-900 px-4 py-16">
      <div className="max-w-5xl mx-auto flex flex-col gap-8">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-white">Candidate Rankings</h1>
          <p className="text-slate-400 mt-1 text-sm">Enter a job ID to fetch and view ranked candidates.</p>
        </div>

        {/* Fetch form */}
        <form onSubmit={handleFetch} className="flex items-end gap-3">
          <div className="flex flex-col gap-1.5 w-56">
            <label htmlFor="job-id" className="text-sm font-medium text-slate-300">
              Job ID
            </label>
            <input
              id="job-id"
              type="text"
              required
              value={jobId}
              onChange={(e) => setJobId(e.target.value)}
              placeholder="e.g. 42"
              className="rounded-lg bg-slate-700 border border-slate-600 px-4 py-2.5 text-white placeholder-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white transition-all hover:bg-indigo-500 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <>
                <svg className="animate-spin w-4 h-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
                </svg>
                Fetching…
              </>
            ) : (
              <>
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
                  <path fillRule="evenodd" d="M10.868 2.884c-.321-.772-1.415-.772-1.736 0l-1.83 4.401-4.753.381c-.833.067-1.171 1.107-.536 1.651l3.62 3.102-1.106 4.637c-.194.813.691 1.456 1.405 1.02L10 15.591l4.069 2.485c.713.436 1.598-.207 1.404-1.02l-1.106-4.637 3.62-3.102c.635-.544.297-1.584-.536-1.65l-4.752-.382-1.83-4.401Z" clipRule="evenodd" />
                </svg>
                Fetch Rankings
              </>
            )}
          </button>
        </form>

        {/* Outreach error */}
        {outreachError && (
          <p className="text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3">
            {outreachError}
          </p>
        )}

        {/* Error */}
        {error && (
          <p className="text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3">
            {error}
          </p>
        )}

        {/* Empty state */}
        {candidates !== null && candidates.length === 0 && (
          <div className="text-center py-16 text-slate-500">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-10 h-10 mx-auto mb-3 opacity-40">
              <path fillRule="evenodd" d="M7.5 6a4.5 4.5 0 1 1 9 0 4.5 4.5 0 0 1-9 0ZM3.751 20.105a8.25 8.25 0 0 1 16.498 0 .75.75 0 0 1-.437.695A18.683 18.683 0 0 1 12 22.5c-2.786 0-5.433-.608-7.812-1.7a.75.75 0 0 1-.438-.695Z" clipRule="evenodd" />
            </svg>
            <p className="text-sm">No candidates found for this job.</p>
          </div>
        )}

        {/* Table */}
        {candidates && candidates.length > 0 && (
          <div className="overflow-x-auto rounded-xl border border-slate-700 shadow-xl">
            <table className="w-full text-sm text-left">
              <thead>
                <tr className="bg-slate-700/60 text-slate-400 uppercase text-xs tracking-wider">
                  <th className="px-5 py-3.5 font-semibold w-16">Rank</th>
                  <th className="px-5 py-3.5 font-semibold">Name</th>
                  <th className="px-5 py-3.5 font-semibold">Email</th>
                  <th className="px-5 py-3.5 font-semibold w-24 text-right">Score</th>
                  <th className="px-5 py-3.5 font-semibold">Reason</th>
                  <th className="px-5 py-3.5 font-semibold w-40"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/60">
                {candidates.map((c, i) => (
                  <tr
                    key={i}
                    className="bg-slate-800 hover:bg-slate-700/50 transition-colors"
                  >
                    <td className="px-5 py-4">
                      <span className={`inline-flex items-center justify-center w-7 h-7 rounded-full text-xs font-bold
                        ${i === 0 ? "bg-yellow-500/15 text-yellow-400 ring-1 ring-yellow-500/30" :
                          i === 1 ? "bg-slate-500/15 text-slate-300 ring-1 ring-slate-500/30" :
                          i === 2 ? "bg-orange-500/15 text-orange-400 ring-1 ring-orange-500/30" :
                          "bg-slate-700 text-slate-400"}`}>
                        {c.rank ?? i + 1}
                      </span>
                    </td>
                    <td className="px-5 py-4 font-medium text-white">{c.name}</td>
                    <td className="px-5 py-4 text-slate-400">{c.email}</td>
                    <td className="px-5 py-4 text-right">
                      <span className={`font-semibold tabular-nums
                        ${c.score >= 80 ? "text-green-400" :
                          c.score >= 60 ? "text-yellow-400" :
                          "text-red-400"}`}>
                        {c.score}
                      </span>
                    </td>
                    <td className="px-5 py-4 text-slate-400 max-w-xs">{c.reason}</td>
                    <td className="px-5 py-4">
                      {(() => {
                        const candidateId = c.candidate_id ?? c.id ?? i;
                        const isLoading = outreachLoading === candidateId;
                        return (
                          <button
                            onClick={() => handleOutreach(c, i)}
                            disabled={outreachLoading !== null}
                            className="inline-flex items-center gap-1.5 rounded-lg bg-slate-700 px-3 py-1.5 text-xs font-semibold text-slate-200 ring-1 ring-slate-600 transition-all hover:bg-indigo-600 hover:ring-indigo-500 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            {isLoading ? (
                              <svg className="animate-spin w-3 h-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
                              </svg>
                            ) : (
                              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-3 h-3">
                                <path d="M3.105 2.288a.75.75 0 0 0-.826.95l1.414 4.926A1.5 1.5 0 0 0 5.135 9.25h6.115a.75.75 0 0 1 0 1.5H5.135a1.5 1.5 0 0 0-1.442 1.086l-1.414 4.926a.75.75 0 0 0 .826.95 28.897 28.897 0 0 0 15.293-7.155.75.75 0 0 0 0-1.114A28.897 28.897 0 0 0 3.105 2.288Z" />
                              </svg>
                            )}
                            {isLoading ? "Generating…" : "Generate Outreach"}
                          </button>
                        );
                      })()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Outreach Modal */}
      {outreachModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm px-4"
          onClick={(e) => { if (e.target === e.currentTarget) setOutreachModal(null); }}
        >
          <div className="bg-slate-800 border border-slate-700 rounded-2xl shadow-2xl w-full max-w-xl">
            {/* Modal header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700">
              <div>
                <h2 className="text-base font-semibold text-white">Outreach Email</h2>
                <p className="text-xs text-slate-400 mt-0.5">For {outreachModal.candidateName}</p>
              </div>
              <button
                onClick={() => setOutreachModal(null)}
                className="rounded-lg p-1.5 text-slate-400 hover:text-white hover:bg-slate-700 transition"
              >
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
                  <path d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22Z" />
                </svg>
              </button>
            </div>
            {/* Modal body */}
            <div className="px-6 py-5 flex flex-col gap-4">
              <div className="flex flex-col gap-1.5">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">Subject</span>
                <p className="text-sm text-white bg-slate-700/60 rounded-lg px-4 py-2.5 border border-slate-700">
                  {outreachModal.subject}
                </p>
              </div>
              <div className="flex flex-col gap-1.5">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">Body</span>
                <p className="text-sm text-slate-300 bg-slate-700/60 rounded-lg px-4 py-3 border border-slate-700 whitespace-pre-wrap leading-relaxed">
                  {outreachModal.body}
                </p>
              </div>
            </div>
            {/* Modal footer */}
            <div className="flex justify-end gap-3 px-6 py-4 border-t border-slate-700">
              <button
                onClick={() => {
                  navigator.clipboard.writeText(
                    `Subject: ${outreachModal.subject}\n\n${outreachModal.body}`
                  );
                }}
                className="inline-flex items-center gap-1.5 rounded-lg bg-slate-700 px-4 py-2 text-sm font-semibold text-slate-200 ring-1 ring-slate-600 transition hover:bg-slate-600"
              >
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
                  <path d="M7 3.5A1.5 1.5 0 0 1 8.5 2h3.879a1.5 1.5 0 0 1 1.06.44l3.122 3.12A1.5 1.5 0 0 1 17 6.622V12.5a1.5 1.5 0 0 1-1.5 1.5h-1v-3.379a3 3 0 0 0-.879-2.121L10.5 5.379A3 3 0 0 0 8.379 4.5H7v-1Z" />
                  <path d="M4.5 6A1.5 1.5 0 0 0 3 7.5v9A1.5 1.5 0 0 0 4.5 18h7a1.5 1.5 0 0 0 1.5-1.5v-5.879a1.5 1.5 0 0 0-.44-1.06L9.44 6.439A1.5 1.5 0 0 0 8.378 6H4.5Z" />
                </svg>
                Copy
              </button>
              <button
                onClick={() => setOutreachModal(null)}
                className="inline-flex items-center rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-indigo-500"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
