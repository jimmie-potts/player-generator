import type {
  ComponentAdjustment,
  Direction,
  FormulaDocument,
  PercentileAnchor,
  PreviewAdjustments,
  RatingScaleAdjustment,
} from "../api/types";

export interface ComponentEditorState {
  metric: string;
  baselineWeight: number;
  weight: number;
  baselineDirection: Direction;
  direction: Direction;
}

export interface AttributeEditorState {
  name: string;
  ratingScale: string;
  components: ComponentEditorState[];
}

export interface RatingScaleEditorState {
  name: string;
  minimum: number;
  maximum: number;
  baselineAnchors: PercentileAnchor[];
  anchors: PercentileAnchor[];
}

export interface FormulaEditorState {
  baseFormulaVersion: string;
  initialProposalVersion: string;
  proposalVersion: string;
  attributes: AttributeEditorState[];
  ratingScales: RatingScaleEditorState[];
}

export interface EditorValidationIssue {
  path: string;
  code:
    | "empty_version"
    | "invalid_direction"
    | "invalid_weight"
    | "invalid_weight_sum"
    | "invalid_anchors"
    | "invalid_percentile"
    | "invalid_rating";
  message: string;
}

function cloneAnchors(anchors: readonly PercentileAnchor[]): PercentileAnchor[] {
  return anchors.map((anchor) => ({ ...anchor }));
}

export function createFormulaEditorState(
  document: FormulaDocument,
  initialProposalVersion = "",
): FormulaEditorState {
  return {
    baseFormulaVersion: document.formulaVersion,
    initialProposalVersion,
    proposalVersion: initialProposalVersion,
    attributes: document.attributes.map((attribute) => ({
      name: attribute.name,
      ratingScale: attribute.ratingScale,
      components: attribute.components.map((component) => ({
        metric: component.metric,
        baselineWeight: component.weight,
        weight: component.weight,
        baselineDirection: component.direction,
        direction: component.direction,
      })),
    })),
    ratingScales: Object.entries(document.ratingScales).map(([name, scale]) => ({
      name,
      minimum: scale.minimum,
      maximum: scale.maximum,
      baselineAnchors: cloneAnchors(scale.anchors),
      anchors: cloneAnchors(scale.anchors),
    })),
  };
}

export function setProposalVersion(
  state: FormulaEditorState,
  proposalVersion: string,
): FormulaEditorState {
  return { ...state, proposalVersion };
}

function updateAttribute(
  state: FormulaEditorState,
  attributeName: string,
  update: (attribute: AttributeEditorState) => AttributeEditorState,
): FormulaEditorState {
  let found = false;
  const attributes = state.attributes.map((attribute) => {
    if (attribute.name !== attributeName) {
      return attribute;
    }
    found = true;
    return update(attribute);
  });
  if (!found) {
    throw new Error(`Unknown formula attribute ${attributeName}.`);
  }
  return { ...state, attributes };
}

function updateComponent(
  state: FormulaEditorState,
  attributeName: string,
  metric: string,
  update: (component: ComponentEditorState) => ComponentEditorState,
): FormulaEditorState {
  return updateAttribute(state, attributeName, (attribute) => {
    let found = false;
    const components = attribute.components.map((component) => {
      if (component.metric !== metric) {
        return component;
      }
      found = true;
      return update(component);
    });
    if (!found) {
      throw new Error(`Metric ${metric} is not a component of ${attributeName}.`);
    }
    return { ...attribute, components };
  });
}

export function setComponentWeight(
  state: FormulaEditorState,
  attributeName: string,
  metric: string,
  weight: number,
): FormulaEditorState {
  return updateComponent(state, attributeName, metric, (component) => ({
    ...component,
    weight,
  }));
}

export function setComponentDirection(
  state: FormulaEditorState,
  attributeName: string,
  metric: string,
  direction: Direction,
): FormulaEditorState {
  return updateComponent(state, attributeName, metric, (component) => ({
    ...component,
    direction,
  }));
}

export function setRatingScaleAnchors(
  state: FormulaEditorState,
  scaleName: string,
  anchors: readonly PercentileAnchor[],
): FormulaEditorState {
  let found = false;
  const ratingScales = state.ratingScales.map((scale) => {
    if (scale.name !== scaleName) {
      return scale;
    }
    found = true;
    return { ...scale, anchors: cloneAnchors(anchors) };
  });
  if (!found) {
    throw new Error(`Unknown formula rating scale ${scaleName}.`);
  }
  return { ...state, ratingScales };
}

function anchorsEqual(
  left: readonly PercentileAnchor[],
  right: readonly PercentileAnchor[],
): boolean {
  return (
    left.length === right.length &&
    left.every(
      (anchor, index) =>
        anchor.percentile === right[index]?.percentile && anchor.rating === right[index]?.rating,
    )
  );
}

export function isAttributeDirty(attribute: AttributeEditorState): boolean {
  return attribute.components.some(
    (component) =>
      component.weight !== component.baselineWeight ||
      component.direction !== component.baselineDirection,
  );
}

export function isRatingScaleDirty(scale: RatingScaleEditorState): boolean {
  return !anchorsEqual(scale.anchors, scale.baselineAnchors);
}

export function dirtyAttributeNames(state: FormulaEditorState): string[] {
  return state.attributes.filter(isAttributeDirty).map((attribute) => attribute.name);
}

export function dirtyRatingScaleNames(state: FormulaEditorState): string[] {
  return state.ratingScales.filter(isRatingScaleDirty).map((scale) => scale.name);
}

export function validateFormulaEditorState(
  state: FormulaEditorState,
): EditorValidationIssue[] {
  const issues: EditorValidationIssue[] = [];
  if (!state.proposalVersion.trim()) {
    issues.push({
      path: "adjustments.formulaVersion",
      code: "empty_version",
      message: "A proposed formula version is required.",
    });
  }

  for (const attribute of state.attributes) {
    let allWeightsValid = true;
    let weightSum = 0;
    for (const component of attribute.components) {
      const path = `attributes.${attribute.name}.components.${component.metric}`;
      if (!Number.isFinite(component.weight) || component.weight < 0) {
        allWeightsValid = false;
        issues.push({
          path: `${path}.weight`,
          code: "invalid_weight",
          message: "Weight must be a finite, nonnegative number.",
        });
      } else {
        weightSum += component.weight;
      }
      if (component.direction !== "higher" && component.direction !== "lower") {
        issues.push({
          path: `${path}.direction`,
          code: "invalid_direction",
          message: "Direction must be higher or lower.",
        });
      }
    }
    if (allWeightsValid && weightSum <= 0) {
      issues.push({
        path: `attributes.${attribute.name}.components`,
        code: "invalid_weight_sum",
        message: "At least one component weight must be greater than zero.",
      });
    }
  }

  for (const scale of state.ratingScales) {
    const path = `ratingScales.${scale.name}.anchors`;
    if (scale.anchors.length < 2) {
      issues.push({
        path,
        code: "invalid_anchors",
        message: "A rating scale requires at least two anchors.",
      });
      continue;
    }
    if (scale.anchors[0]?.percentile !== 0) {
      issues.push({
        path,
        code: "invalid_anchors",
        message: "The first anchor must start at percentile 0.",
      });
    }
    if (scale.anchors.at(-1)?.percentile !== 1) {
      issues.push({
        path,
        code: "invalid_anchors",
        message: "The final anchor must end at percentile 1.",
      });
    }

    scale.anchors.forEach((anchor, index) => {
      const anchorPath = `${path}.${index}`;
      if (
        !Number.isFinite(anchor.percentile) ||
        anchor.percentile < 0 ||
        anchor.percentile > 1
      ) {
        issues.push({
          path: `${anchorPath}.percentile`,
          code: "invalid_percentile",
          message: "Anchor percentile must be between 0 and 1.",
        });
      }
      if (!Number.isFinite(anchor.rating) || anchor.rating < 25 || anchor.rating > 99) {
        issues.push({
          path: `${anchorPath}.rating`,
          code: "invalid_rating",
          message: "Anchor rating must be between 25 and 99.",
        });
      }
      const previous = scale.anchors[index - 1];
      if (previous && anchor.percentile <= previous.percentile) {
        issues.push({
          path: `${anchorPath}.percentile`,
          code: "invalid_anchors",
          message: "Anchor percentiles must be strictly increasing.",
        });
      }
      if (previous && anchor.rating < previous.rating) {
        issues.push({
          path: `${anchorPath}.rating`,
          code: "invalid_anchors",
          message: "Anchor ratings must be nondecreasing.",
        });
      }
    });
  }
  return issues;
}

export function buildPreviewAdjustments(state: FormulaEditorState): PreviewAdjustments {
  const components: ComponentAdjustment[] = [];
  for (const attribute of state.attributes) {
    for (const component of attribute.components) {
      const adjustment: ComponentAdjustment = {
        attribute: attribute.name,
        metric: component.metric,
      };
      if (component.weight !== component.baselineWeight) {
        adjustment.weight = component.weight;
      }
      if (component.direction !== component.baselineDirection) {
        adjustment.inverseDirection = true;
      }
      if (adjustment.weight !== undefined || adjustment.inverseDirection !== undefined) {
        components.push(adjustment);
      }
    }
  }

  const ratingScales: RatingScaleAdjustment[] = state.ratingScales
    .filter(isRatingScaleDirty)
    .map((scale) => ({
      scale: scale.name,
      anchors: cloneAnchors(scale.anchors),
    }));

  return {
    formulaVersion: state.proposalVersion.trim(),
    components,
    ratingScales,
  };
}

export function resetAttribute(
  state: FormulaEditorState,
  attributeName: string,
): FormulaEditorState {
  return updateAttribute(state, attributeName, (attribute) => ({
    ...attribute,
    components: attribute.components.map((component) => ({
      ...component,
      weight: component.baselineWeight,
      direction: component.baselineDirection,
    })),
  }));
}

export function resetRatingScale(
  state: FormulaEditorState,
  scaleName: string,
): FormulaEditorState {
  return setRatingScaleAnchors(
    state,
    scaleName,
    state.ratingScales.find((scale) => scale.name === scaleName)?.baselineAnchors ?? [],
  );
}

export function resetAll(state: FormulaEditorState): FormulaEditorState {
  return {
    ...state,
    proposalVersion: state.initialProposalVersion,
    attributes: state.attributes.map((attribute) => ({
      ...attribute,
      components: attribute.components.map((component) => ({
        ...component,
        weight: component.baselineWeight,
        direction: component.baselineDirection,
      })),
    })),
    ratingScales: state.ratingScales.map((scale) => ({
      ...scale,
      anchors: cloneAnchors(scale.baselineAnchors),
    })),
  };
}
