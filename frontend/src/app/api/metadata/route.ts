import { type NextRequest, NextResponse } from 'next/server';

export async function GET(req: NextRequest) {
  const url = req.nextUrl.searchParams.get('url');
  if (!url) {
    return NextResponse.json({ error: 'URL parameter is required' }, { status: 400 });
  }

  try {
    let oembedUrl = '';

    if (url.includes('youtube.com') || url.includes('youtu.be')) {
      oembedUrl = `https://www.youtube.com/oembed?url=${encodeURIComponent(url)}&format=json`;
    } else if (url.includes('reddit.com')) {
      oembedUrl = `https://www.reddit.com/oembed?url=${encodeURIComponent(url)}&format=json`;
    } else if (url.includes('twitter.com') || url.includes('x.com')) {
      oembedUrl = `https://publish.twitter.com/oembed?url=${encodeURIComponent(url)}`;
    }

    if (oembedUrl) {
      const response = await fetch(oembedUrl);
      if (response.ok) {
        const data = await response.json();
        return NextResponse.json({
          thumbnail: data.thumbnail_url || data.url,
          title: data.title,
          author: data.author_name,
        });
      }
    }

    // Fallback for Reddit if oembed fails or other sites
    // For Reddit, we can try the .json trick on the server side
    if (url.includes('reddit.com')) {
      const jsonUrl = url.endsWith('/') ? `${url.slice(0, -1)}.json` : `${url}.json`;
      const response = await fetch(jsonUrl);
      if (response.ok) {
        const data = await response.json();
        // Reddit JSON structure is complex: [ { data: { children: [ { data: { thumbnail: ... } } ] } } ]
        const thumbnail = data?.[0]?.data?.children?.[0]?.data?.thumbnail;
        if (thumbnail && thumbnail !== 'self' && thumbnail !== 'default') {
          return NextResponse.json({ thumbnail });
        }
      }
    }

    return NextResponse.json({ error: 'Could not fetch metadata' }, { status: 404 });
  } catch (_err) {
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
