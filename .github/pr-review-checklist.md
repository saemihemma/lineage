# PR Review Checklist

Use this checklist when reviewing pull requests:

## Code Quality

- [ ] Code follows project style guidelines (PEP 8 for Python, TypeScript conventions for frontend)
- [ ] Code is readable and well-commented
- [ ] Variable and function names are meaningful
- [ ] No hardcoded secrets or credentials
- [ ] No console.log/debug statements left in production code (backend logging is fine)

## Testing

- [ ] Smoke tests pass (`python3 -m pytest backend/tests/test_smoke.py -v`)
- [ ] All relevant tests pass
- [ ] New tests added for new functionality (if applicable)
- [ ] Test coverage maintained or improved

## Functionality

- [ ] Changes work as described
- [ ] No breaking changes (or breaking changes are documented)
- [ ] Backward compatibility maintained (if applicable)
- [ ] Edge cases handled appropriately

## Security

- [ ] No sensitive data exposed
- [ ] Input validation in place
- [ ] No SQL injection vulnerabilities
- [ ] No XSS vulnerabilities (if frontend changes)
- [ ] CSRF protection maintained (if backend changes)

## Documentation

- [ ] README updated if needed
- [ ] Code comments added for complex logic
- [ ] API documentation updated (if backend changes)
- [ ] Changelog updated (if applicable)

## Performance

- [ ] No obvious performance issues
- [ ] Database queries optimized (if applicable)
- [ ] Frontend bundle size reasonable (if applicable)

## UI/UX (if applicable)

- [ ] UI changes are intuitive
- [ ] Responsive design maintained
- [ ] Accessibility considered
- [ ] Screenshots provided for visual changes

## Git

- [ ] Commit messages are clear and descriptive
- [ ] PR is based on latest `web-version` branch
- [ ] No merge conflicts
- [ ] Branch can be merged cleanly

## Additional Notes

<!-- Add any additional notes or concerns here -->

