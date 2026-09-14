import pytest
from app.browser.search_engine import DirectBrowserSearch


def test_unwrap_ddg_url():
    raw = "//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fresearch%2Fai&rut=test"
    unwrapped = DirectBrowserSearch._unwrap_ddg_url(raw)
    assert unwrapped == "https://example.com/research/ai"


def test_parse_duckduckgo_html():
    sample_html = """
    <html>
      <body>
        <div class="result results_links">
          <h2 class="result__title">
            <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fqwen-models">
              Qwen 2.5 Architecture and Benchmarks
            </a>
          </h2>
          <a class="result__snippet">
            An in-depth analysis of Alibaba's Qwen open-weights models and inference efficiency.
          </a>
        </div>
        <div class="result results_links result--ad">
          <a class="result__a" href="https://bad-ad.com">Sponsored Ad</a>
        </div>
      </body>
    </html>
    """
    results = DirectBrowserSearch.parse_duckduckgo_html(sample_html)
    assert len(results) == 1
    assert results[0].title == "Qwen 2.5 Architecture and Benchmarks"
    assert results[0].url == "https://example.com/qwen-models"
    assert "open-weights" in results[0].snippet
    assert results[0].engine == "duckduckgo"


def test_parse_bing_html():
    sample_html = """
    <html>
      <body>
        <ol id="b_results">
          <li class="b_algo">
            <h2>
              <a href="https://example.org/playwright-guide">Modern Playwright Guide</a>
            </h2>
            <div class="b_caption">
              <p>Headless browser automation without commercial APIs.</p>
            </div>
          </li>
        </ol>
      </body>
    </html>
    """
    results = DirectBrowserSearch.parse_bing_html(sample_html)
    assert len(results) == 1
    assert results[0].title == "Modern Playwright Guide"
    assert results[0].url == "https://example.org/playwright-guide"
    assert "Headless browser automation" in results[0].snippet
    assert results[0].engine == "bing"
