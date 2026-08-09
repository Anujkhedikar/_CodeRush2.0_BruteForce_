export async function fetchMemeStyles(url: string): Promise<any> {
  const response = await fetch(url)
  if (!response.ok) {
    throw new Error(`Failed to fetch meme styles: HTTP ${response.status}`)
  }
  return response.json()
}
