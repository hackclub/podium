// Global state for tracking if user has submitted a project
// Used to conditionally show/hide navigation in the sidebar

let hasProject = $state(false);
let initialized = $state(false);

export function setHasProject(value: boolean) {
  hasProject = value;
  initialized = true;
}

export function getHasProject(): boolean {
  return hasProject;
}

export function isProjectStateInitialized(): boolean {
  return initialized;
}

export function resetProjectState() {
  hasProject = false;
  initialized = false;
}
