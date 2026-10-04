import { useEffect, useState } from 'react'
import './App.css'

type Summary = {
  total_products: number
  total_views: number
  total_sales: number
}

type Product = {
  product_id: number
  name: string
}

const api = {
  summary: '/api/analytics/summary',
  products: '/api/products',
}

function App() {
  const [summary, setSummary] = useState<Summary | null>(null)
  const [products, setProducts] = useState<Product[]>([])
  const [error, setError] = useState('')

  useEffect(() => {
    const load = async () => {
      try {
        const [summaryResponse, productsResponse] = await Promise.all([
          fetch(api.summary),
          fetch(api.products),
        ])

        if (!summaryResponse.ok || !productsResponse.ok) {
          throw new Error('Failed to load analytics data')
        }

        const summaryData = await summaryResponse.json()
        const productsData = await productsResponse.json()

        setSummary(summaryData)
        setProducts(productsData)
      } catch (loadError) {
        setError(
          loadError instanceof Error ? loadError.message : 'Could not load analytics data',
        )
      }
    }

    void load()
  }, [])

  return (
    <main className="dashboard">
      <header className="topbar">
        <div>
          <p className="eyebrow">AI Product Analytics Copilot</p>
          <h1>Business overview</h1>
        </div>
      </header>

      {error ? (
        <div className="error">{error}</div>
      ) : null}

      <section className="stats-grid">
        <article className="stat-card">
          <span>Total products</span>
          <strong>{summary?.total_products ?? 0}</strong>
        </article>
        <article className="stat-card">
          <span>Total views</span>
          <strong>{summary?.total_views ?? 0}</strong>
        </article>
        <article className="stat-card">
          <span>Total sales</span>
          <strong>{summary?.total_sales ?? 0}</strong>
        </article>
      </section>

      <section className="panel">
        <div className="panel-header">
          <h2>Products</h2>
        </div>

        <ul className="product-list">
          {products.map((product) => (
            <li key={product.product_id} className="product-item">
              <div>
                <p className="product-id">Product #{product.product_id}</p>
                <h3>{product.name}</h3>
              </div>
            </li>
          ))}
        </ul>
      </section>
    </main>
  )
}

export default App
