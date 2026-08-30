# Changelog

## [1.3.0](https://github.com/trash-panda-v91-beta/donetick-mcp/compare/v1.2.0...v1.3.0) (2026-08-30)


### Features

* **deps:** update hk ( 1.54.1 ➔ 1.55.0 ) ([#37](https://github.com/trash-panda-v91-beta/donetick-mcp/issues/37)) ([8d8bb1a](https://github.com/trash-panda-v91-beta/donetick-mcp/commit/8d8bb1aedd7926f4e9d50802eebbe2aca7479abd))


### Bug Fixes

* **deps:** update fastmcp ( 4.0.0b3 ➔ 4.0.0b4 ) ([#41](https://github.com/trash-panda-v91-beta/donetick-mcp/issues/41)) ([89c6953](https://github.com/trash-panda-v91-beta/donetick-mcp/commit/89c69539a2f5bd20ff6288e7ab145fd8c6601072))


### Continuous Integration

* **github-action:** update renovatebot/github-action ( v46.2.2 ➔ v46.2.4 ) ([#40](https://github.com/trash-panda-v91-beta/donetick-mcp/issues/40)) ([f09b823](https://github.com/trash-panda-v91-beta/donetick-mcp/commit/f09b8234276c06ce60b04b3c04870c522a138d46))

## [1.2.0](https://github.com/trash-panda-v91-beta/donetick-mcp/compare/v1.1.0...v1.2.0) (2026-08-18)


### Features

* add chores, things, and project tools for the full api ([#34](https://github.com/trash-panda-v91-beta/donetick-mcp/issues/34)) ([2bf9de8](https://github.com/trash-panda-v91-beta/donetick-mcp/commit/2bf9de852904bad33402e4dd3f960d39be2fc4ca))
* add circle management tools ([#35](https://github.com/trash-panda-v91-beta/donetick-mcp/issues/35)) ([05ca9fe](https://github.com/trash-panda-v91-beta/donetick-mcp/commit/05ca9fee6d7a1bdcc718ce397dcd4e45d10c0de3))
* add create_thing tool ([#33](https://github.com/trash-panda-v91-beta/donetick-mcp/issues/33)) ([4206cf1](https://github.com/trash-panda-v91-beta/donetick-mcp/commit/4206cf1f5941b281ba1688d2f145ea91c8a764b3))


### Bug Fixes

* **client:** drop trailing slash on circle members endpoint (donetick redirects it) ([#30](https://github.com/trash-panda-v91-beta/donetick-mcp/issues/30)) ([13a91c5](https://github.com/trash-panda-v91-beta/donetick-mcp/commit/13a91c5f0942b149f7e9e671bd5d46e5cbdaa2a7))
* **client:** match live donetick API shapes for details, priority, complete, assignees ([#32](https://github.com/trash-panda-v91-beta/donetick-mcp/issues/32)) ([6994ec8](https://github.com/trash-panda-v91-beta/donetick-mcp/commit/6994ec8235bde14fc643b50060a758ac784d7983))

## [1.1.0](https://github.com/trash-panda-v91-beta/donetick-mcp/compare/v1.0.0...v1.1.0) (2026-08-18)


### Features

* **config:** support plaintext http base URLs for cluster deployment ([#20](https://github.com/trash-panda-v91-beta/donetick-mcp/issues/20)) ([ad335c7](https://github.com/trash-panda-v91-beta/donetick-mcp/commit/ad335c73b9f55a7ec72157999086eb56c6bea8d5))


### Continuous Integration

* **github-action:** update jdx/mise-action ( 7e36c90 ➔ 3c2e0cf ) ([#23](https://github.com/trash-panda-v91-beta/donetick-mcp/issues/23)) ([ad8b4a3](https://github.com/trash-panda-v91-beta/donetick-mcp/commit/ad8b4a3d484f9f857f59efcf856be5d974a4d03f))

## [1.0.0](https://github.com/trash-panda-v91-beta/donetick-mcp/compare/v0.1.1...v1.0.0) (2026-08-18)


### ⚠ BREAKING CHANGES

* **github-action:** Update actions/checkout ( v4.4.0 ➔ v7.0.1 ) ([#7](https://github.com/trash-panda-v91-beta/donetick-mcp/issues/7))
* **github-action:** Update amannn/action-semantic-pull-request ( v5.5.3 ➔ v6.1.1 ) ([#8](https://github.com/trash-panda-v91-beta/donetick-mcp/issues/8))
* **github-action:** Update docker/build-push-action ( v6.19.2 ➔ v7.3.0 ) ([#9](https://github.com/trash-panda-v91-beta/donetick-mcp/issues/9))
* **github-action:** Update docker/login-action ( v3.7.0 ➔ v4.6.0 ) ([#10](https://github.com/trash-panda-v91-beta/donetick-mcp/issues/10))
* **github-action:** Update docker/metadata-action ( v5.10.0 ➔ v6.2.0 ) ([#11](https://github.com/trash-panda-v91-beta/donetick-mcp/issues/11))
* **github-action:** Update docker/setup-buildx-action ( v3.12.0 ➔ v4.2.0 ) ([#12](https://github.com/trash-panda-v91-beta/donetick-mcp/issues/12))
* **github-action:** Update GitHub Artifact Actions ([#13](https://github.com/trash-panda-v91-beta/donetick-mcp/issues/13))
* **github-action:** Update googleapis/release-please-action ( v4.4.0 ➔ v5.0.0 ) ([#14](https://github.com/trash-panda-v91-beta/donetick-mcp/issues/14))

### Bug Fixes

* **release:** keep uv.lock in sync when release-please bumps the version ([#16](https://github.com/trash-panda-v91-beta/donetick-mcp/issues/16)) ([f8a46aa](https://github.com/trash-panda-v91-beta/donetick-mcp/commit/f8a46aa4de5a703cce74907deb9755be73129db2))


### Continuous Integration

* **github-action:** Update actions/checkout ( v4.4.0 ➔ v7.0.1 ) ([#7](https://github.com/trash-panda-v91-beta/donetick-mcp/issues/7)) ([88d6471](https://github.com/trash-panda-v91-beta/donetick-mcp/commit/88d6471ed32eec422634597e28ac20daebf79cc9))
* **github-action:** Update amannn/action-semantic-pull-request ( v5.5.3 ➔ v6.1.1 ) ([#8](https://github.com/trash-panda-v91-beta/donetick-mcp/issues/8)) ([844826b](https://github.com/trash-panda-v91-beta/donetick-mcp/commit/844826b8ea818abb7842bd6288858dc9e8f00ba7))
* **github-action:** Update docker/build-push-action ( v6.19.2 ➔ v7.3.0 ) ([#9](https://github.com/trash-panda-v91-beta/donetick-mcp/issues/9)) ([5d2f519](https://github.com/trash-panda-v91-beta/donetick-mcp/commit/5d2f5197e992780b63a81a3915395dc414be70af))
* **github-action:** Update docker/login-action ( v3.7.0 ➔ v4.6.0 ) ([#10](https://github.com/trash-panda-v91-beta/donetick-mcp/issues/10)) ([1ba2e83](https://github.com/trash-panda-v91-beta/donetick-mcp/commit/1ba2e836d6fcce2d74291b72c486257469656407))
* **github-action:** Update docker/metadata-action ( v5.10.0 ➔ v6.2.0 ) ([#11](https://github.com/trash-panda-v91-beta/donetick-mcp/issues/11)) ([a7d3cda](https://github.com/trash-panda-v91-beta/donetick-mcp/commit/a7d3cda9fef311ab3b0d6e7a1c51827e183ca52c))
* **github-action:** Update docker/setup-buildx-action ( v3.12.0 ➔ v4.2.0 ) ([#12](https://github.com/trash-panda-v91-beta/donetick-mcp/issues/12)) ([ce78ace](https://github.com/trash-panda-v91-beta/donetick-mcp/commit/ce78acebd6f4b7b0657cba4a97da0a434d98a7cb))
* **github-action:** Update GitHub Artifact Actions ([#13](https://github.com/trash-panda-v91-beta/donetick-mcp/issues/13)) ([700ca7d](https://github.com/trash-panda-v91-beta/donetick-mcp/commit/700ca7dd6a9d53807db3dbfb760947cf72d0219e))
* **github-action:** Update googleapis/release-please-action ( v4.4.0 ➔ v5.0.0 ) ([#14](https://github.com/trash-panda-v91-beta/donetick-mcp/issues/14)) ([1206a86](https://github.com/trash-panda-v91-beta/donetick-mcp/commit/1206a86f5e3eba8641076a548cc32889572b4091))

## [0.1.1](https://github.com/trash-panda-v91-beta/donetick-mcp/compare/v0.1.0...v0.1.1) (2026-08-18)


### Features

* bootstrap ([d3837b0](https://github.com/trash-panda-v91-beta/donetick-mcp/commit/d3837b0cbee95bda72df75cfe8771e369b06385c))


### Bug Fixes

* exclude CHANGELOG.md from rumdl glob ([#3](https://github.com/trash-panda-v91-beta/donetick-mcp/issues/3)) ([6c7ab32](https://github.com/trash-panda-v91-beta/donetick-mcp/commit/6c7ab32c4096ebbe2e2ebd69853bee9cf51aa8c7))


### Code Refactoring

* slim dead code and unused scope ([#1](https://github.com/trash-panda-v91-beta/donetick-mcp/issues/1)) ([2c7967a](https://github.com/trash-panda-v91-beta/donetick-mcp/commit/2c7967a303260f532f27e83df9fa15d62be21691))
