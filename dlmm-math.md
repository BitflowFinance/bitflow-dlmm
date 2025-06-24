DLMM Variables and Formulas
Variables
$N$
Number of bins in the pool
$P_0$
Lowest priced bin
$P_{n-1}$
Highest priced bin
$s$
Bin step (distance between bins, measured in bps)
$X$
Token X (BTC)
$Y$
Token Y (USDC)
$P_i$
Price of the $i$-th bin:
$$
P_i = P_0 \times (1 + s)^i
$$
$x_i$
Amount of token X in bin $i$
$y_i$
Amount of token Y in bin $i$
$\Delta x_i$
Amount of token X being added to bin $i$
$\Delta y_i$
Amount of token Y being added to bin $i$
$L_i$
Liquidity in bin $i$
$c_i$
Composition factor in bin $i$ (percentage of bin liquidity composed of $Y$):
$$
c_i = \frac{y_i}{L_i}
$$
Formulas
Price of the $i$-th Bin
$$
P_i = P_0 \times (1 + s)^i
$$
Liquidity in Bin $i$
$$
L_i = x_i + \frac{y_i}{P_i}
$$
Total TVL Across All Bins (Invariant)
$$
K = \sum_{i=0}^{N-1} \left( x_i + \frac{y_i}{P_i} \right)
$$
Change in LP Tokens from Liquidity Added Across Bins
$$
\Delta_{LP} = \sum_{i=0}^{N-1} \left( \Delta x_i + \frac{\Delta y_i}{P_i} \right)
$$
Composition Factor and Bin Reserves
$$
c_i = \frac{y_i}{L_i}
$$
$$
y_i = c_i L_i
$$
$$
x_i = \left(1 - c_i\right) \frac{L_i}{P_i}
$$
Swap Price Quotes
Swapping Within a Single Bin
Swap X for Y (within bin $i$):
The price is fixed at $P_i$ for all trades within the bin until the bin is depleted.
$$
\text{If you swap } \Delta x \text{ of X, you receive:} \qquad \Delta y = \min\left(P_i \cdot \Delta x,\, y_i\right)
$$
Swap Y for X (within bin $i$):
$$
\text{If you swap } \Delta y \text{ of Y, you receive:} \qquad \Delta x = \min\left(\frac{\Delta y}{P_i},\, x_i\right)
$$
Swapping Across Multiple Bins
When the swap amount exceeds the available liquidity in the active bin, the swap continues into the next bin(s), each with its own fixed price $P_j$.
Swap X for Y (across bins):
For a total input $\Delta x$, the output is the sum of outputs from each bin traversed:
$$
\Delta y_{\text{total}} = \sum_{j} \min\left(P_j \cdot \Delta x_j,\, y_j\right)
$$
where $\Delta x_j$ is the amount of X swapped in bin $j$, and $P_j = P_0 (1 + s)^j$.
Swap Y for X (across bins):
$$
\Delta x_{\text{total}} = \sum_{j} \min\left(\frac{\Delta y_j}{P_j},\, x_j\right)
$$
where $\Delta y_j$ is the amount of Y swapped in bin $j$.
Notes
All bins except for the active one contain just one type of token (X or Y) because they have been depleted or are waiting to be used. Only the active bin earns trading fees.
The price $P_i$ is uniform within each bin and does not depend on the reserve amounts.
The composition of reserves, $x$ and $y$, are independent of both price and liquidity. The composition factor $c$ describes the percentage of bin liquidity in $y$.