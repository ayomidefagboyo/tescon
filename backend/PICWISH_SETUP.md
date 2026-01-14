# PicWish API Setup Guide

## Getting Started

1. **Sign up for PicWish API**
   - Visit https://picwish.com/api-pricing
   - Create an account and get your API key
   - Choose a pricing plan that fits your needs

2. **Configure API Key**
   - Set the `PICWISH_API_KEY` environment variable
   - Or add it to your `.env` file:
     ```
     PICWISH_API_KEY=your_api_key_here
     ```

3. **Verify API Endpoint**
   - Check PicWish API documentation for the exact endpoint
   - Default endpoint: `https://api.picwish.com/v1/remove-background`
   - If different, set `PICWISH_API_URL` environment variable

## API Request Format

The current implementation uses:
- **Method**: POST
- **Headers**: `X-API-Key: {your_api_key}`
- **Body**: multipart/form-data with image file

If PicWish uses a different format, you may need to adjust:
- Header name (e.g., `X-API-KEY` or `Authorization: Bearer {key}`)
- Form field name (e.g., `image_file` instead of `image`)
- Endpoint URL

## Testing

Test the API connection:
```bash
curl -X POST https://api.picwish.com/v1/remove-background \
  -H "X-API-Key: your_api_key" \
  -F "image=@test_image.jpg" \
  -o output.png
```

## Troubleshooting

- **401 Unauthorized**: Check your API key is correct
- **429 Too Many Requests**: You've hit rate limits, wait and retry
- **400 Bad Request**: Check image format and size limits
- **500 Server Error**: PicWish service issue, retry later

For detailed API documentation, visit: https://picwish.com/background-removal-api-doc

