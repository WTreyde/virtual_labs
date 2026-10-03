import workflow from "../../../examples/workflow.json";
import type { ProjectRequest } from "../types";

/**
 * Client fixture for the project-planning view until Strand B's demo scenario lands: three projects on the
 * example enzyme lab, varied only in dispense and read times (as in backend/tests/test_portfolio.py).
 * The durations are illustrative, not measured.
 */
function project(id: string, units: number, dispense_s: number, read_s: number, extra: Partial<ProjectRequest> = {}): ProjectRequest {
  const wf = structuredClone(workflow) as ProjectRequest["workflow"];
  wf.id = id;
  for (const s of (wf as typeof workflow).steps) {
    if (s.id === "dispense") s.duration_s = dispense_s;
    if (s.id === "read") s.duration_s = read_s;
  }
  return { id, workflow: wf, units, ...extra };
}

/** The order given here is the "naive" order the recommendation is compared against. */
export const exampleProjects: ProjectRequest[] = [
  project("enzyme_campaign_a", 10, 1800, 60),
  project("kinetics_reads_b", 10, 60, 1800),
  project("urgent_retest", 2, 1800, 60, { deadline_h: 4, weight: 5 }),
];
