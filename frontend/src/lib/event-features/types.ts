/**
 * Event Feature System
 *
 * This module defines the interface for pluggable event-specific features.
 * Each event feature (e.g., Daydream) can provide custom validation logic
 * and UI components that integrate seamlessly into the admin dashboard.
 */

import type { ProjectPublic } from "$lib/client/types.gen";
import type { Component } from "svelte";

/**
 * Result of a project validation check
 */
export interface ValidationResult {
  isValid: boolean;
  message: string;
  /** Additional metadata for the validation (e.g., swag eligibility) */
  metadata?: Record<string, any>;
}

/**
 * Project validator function signature
 */
export type ProjectValidator = (
  project: ProjectPublic,
) => ValidationResult | Promise<ValidationResult>;

/**
 * UI component for displaying validation results in the admin leaderboard
 * Props: { validation: ValidationResult, project: Project }
 */
export type ValidationUIComponent = Component<{
  validation: ValidationResult;
  project: ProjectPublic;
}>;

/**
 * Complete event feature definition
 */
export interface EventFeature {
  /** Unique identifier matching the feature flag */
  featureFlag: string;

  /** Display name for the feature */
  name: string;

  /** Validates a project according to this feature's rules */
  validateProject?: ProjectValidator;

  /** Optional custom UI component for displaying validation in admin leaderboard */
  ValidationComponent?: ValidationUIComponent;
}
