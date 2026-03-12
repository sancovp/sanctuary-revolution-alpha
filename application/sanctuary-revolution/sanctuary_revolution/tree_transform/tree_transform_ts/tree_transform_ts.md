# ts-tree-transform/

src/
  core.ts
  validators.ts
  utils.ts
package.json
README.md
```  

```json
// package.json
{
  "name": "ts-tree-transform",
  "version": "0.1.0",
  "main": "dist/index.js",
  "types": "dist/index.d.ts",
  "scripts": {
    "build": "tsc",
    "test": "jest"
  },
  "dependencies": {
    "ml-matrix": "^6.8.0"
  },
  "devDependencies": {
    "typescript": "^4.9.0",
    "jest": "^29.0.0",
    "ts-jest": "^29.0.0",
    "@types/jest": "^29.0.0"
  }
}
```  

```typescript
// src/utils.ts
/**
 * Compute offsets for a property module.
 * Given dims: Record<vertex, dimension>
 * Returns a Record<vertex, startIndex>
 */
export function computeOffsets(dims: Record<string, number>): Record<string, number> {
  const offsets: Record<string, number> = {};
  let idx = 0;
  for (const [v, d] of Object.entries(dims)) {
    offsets[v] = idx;
    idx += d;
  }
  return offsets;
}
```

```typescript
// src/core.ts
import { computeOffsets } from './utils';

/**
 * PropertyModule: per-vertex property vector spaces.
 */
export class PropertyModule {
  public dims: Record<string, number>;
  public totalDim: number;
  public offsets: Record<string, number>;

  constructor(dims: Record<string, number>) {
    this.dims = dims;
    this.totalDim = Object.values(dims).reduce((a, b) => a + b, 0);
    this.offsets = computeOffsets(dims);
  }

  /** Zero vector of length totalDim */
  zeroVector(): Float64Array {
    return new Float64Array(this.totalDim);
  }

  /** Basis vector at given vertex and index */
  basisVector(vertex: string, index: number): Float64Array {
    const vec = new Float64Array(this.totalDim);
    const start = this.offsets[vertex];
    vec[start + index] = 1;
    return vec;
  }
}

/**
 * InclusionMap: injective linear map g: S -> T.
 */
export class InclusionMap {
  public source: PropertyModule;
  public target: PropertyModule;
  public matrix: Float64Array; // row-major: [row0col0, row0col1,...]
  public rows: number;
  public cols: number;

  constructor(
    source: PropertyModule,
    target: PropertyModule,
    matrix: Float64Array
  ) {
    this.source = source;
    this.target = target;
    this.matrix = matrix;
    this.rows = target.totalDim;
    this.cols = source.totalDim;
    this.validateDimensions();
  }

  private validateDimensions(): void {
    if (this.rows * this.cols !== this.matrix.length) {
      throw new Error('Matrix dimensions do not match module dims');
    }
  }

  /** Check injectivity via column rank == cols */
  isInjective(tol = 1e-8): boolean {
    const { SVD } = require('ml-matrix');
    const mat = new (require('ml-matrix').Matrix)(
      Array.from({ length: this.rows }, (_, i) =>
        this.matrix.slice(i * this.cols, i * this.cols + this.cols)
      )
    );
    const svd = new SVD(mat);
    const rank = svd.rank(tol);
    return rank === this.cols;
  }
}
```

```typescript
// src/validators.ts
import { InclusionMap } from './core';
import { Matrix, SVD } from 'ml-matrix';

/**
 * Computes P: T -> Q = T / im(g) as left-nullspace of g.
 * Returns Float64Array of shape (qDim, Tdim) row-major.
 */
export function computeQuotientProjection(
  inc: InclusionMap,
  tol = 1e-8
): Float64Array {
  // g: rows=Tdim, cols=Sdim; we want nullspace of g^T (shape Sdim x Tdim)
  const gMat = new Matrix(
    Array.from({ length: inc.rows }, (_, i) =>
      inc.matrix.slice(i * inc.cols, i * inc.cols + inc.cols)
    )
  );
  const gT = gMat.transpose();
  const svd = new SVD(gT);
  const rank = svd.rank(tol);
  const V = svd.V;
  const qDim = gT.columns - rank;
  const nullspaceRows = V.subMatrix(rank, V.rows - 1, 0, V.columns - 1);

  // Flatten nullspaceRows to Float64Array row-major
  const P = new Float64Array(qDim * inc.rows);
  for (let r = 0; r < qDim; r++) {
    for (let c = 0; c < inc.rows; c++) {
      P[r * inc.rows + c] = nullspaceRows.get(r, c);
    }
  }
  return P;
}

/**
 * Checks exactness: 0->S--g->T--P->Q->0
 */
export function checkExactness(
  inc: InclusionMap,
  P: Float64Array,
  tol = 1e-8
): boolean {
  // 1) g injective
  if (!inc.isInjective(tol)) return false;

  // 2) P @ g == 0
  const rows = P.length / inc.rows;
  // Multiply P (rows x Tdim) by g (Tdim x Sdim)
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < inc.cols; c++) {
      let sum = 0;
      for (let k = 0; k < inc.rows; k++) {
        sum += P[r * inc.rows + k] * inc.matrix[k * inc.cols + c];
      }
      if (Math.abs(sum) > tol) return false;
    }
  }

  // 3) P full row rank (rows == rank)
  const Pmat = new Matrix(rows, inc.rows, P);
  const pRank = new SVD(Pmat).rank(tol);
  if (pRank !== rows) return false;

  return true;
}
