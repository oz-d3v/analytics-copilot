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

type QueryResponse = {
  answer: string
  summary: Summary
}

const api = {
  summary: '/api/analytics/summary',
  products: '/api/products',
  query: '/api/analytics/query',
}

const defaultQuestions = [
  'Give me an overall summary of product performance',
  'Which product has the most sales?',
  'Which product has the most views?',
  'How is product 1 performing?',
]

function App() {
  const [summary, setSummary] = useState<Summary | null>(null)
  const [products, setProducts] = useState<Product[]>([])
  const [question, setQuestion] = useState(defaultQuestions[0])
  const [answer, setAnswer] = useState('')
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

  const handleAsk = async (event: React.FormEvent) => {
    event.preventDefault()

    try {
      const response = await fetch(api.query, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ question }),
      })

      if (!response.ok) {
        throw new Error('Failed to get an answer')
      }

      const data: QueryResponse = await response.json()
      setAnswer(data.answer)
    } catch (askError) {
      setError(
        askError instanceof Error ? askError.message : 'Could not process your question',
      )
    }
  }

  return (
    <main className="dashboard">
      <header className="topbar">
        <div>
          <p className="eyebrow">AI Product Analytics Copilot</p>
          <h1>Business overview</h1>
        </div>
      </header>

      {error ? <div className="error">{error}</div> : null}

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

      <section className="panel ask-panel">
        <div className="panel-header">
          <h2>Ask the analytics assistant</h2>
        </div>

        <div className="quick-prompts">
          {defaultQuestions.map((prompt) => (
            <button
              key={prompt}
              type="button"
              className="quick-prompt"
              onClick={() => setQuestion(prompt)}
            >
              {prompt}
            </button>
          ))}
          {products.map((product) => (
            <button
              key={`product-${product.product_id}`}
              type="button"
              className="quick-prompt"
              onClick={() => setQuestion(`How is product ${product.product_id} performing?`)}
            >
              {`How is ${product.name} performing?`}
            </button>
          ))}
        </div>

        <form onSubmit={handleAsk} className="ask-form">
          <input
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Ask about sales, views, or product performance"
          />
          <button type="submit">Ask</button>
        </form>

        {answer ? <p className="assistant-answer">{answer}</p> : null}
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
