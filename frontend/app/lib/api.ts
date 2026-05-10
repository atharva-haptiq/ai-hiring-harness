const BASE_URL = "/api";

export async function createJob(data: any) {
  const res = await fetch(`${BASE_URL}/job/create`, {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify(data),
  });
  return res.json();
}

export async function generateOutreach(candidate_id: number, job_id: number) {
  const res = await fetch(`${BASE_URL}/outreach`, {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({ candidate_id, job_id }),
  });
  return res.json();
}

export async function rankCandidates(job_id: number) {
  const res = await fetch(`${BASE_URL}/rank`, {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({ job_id }),
  });
  return res.json();
}